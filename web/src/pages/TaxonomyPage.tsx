import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { canManageTaxonomy } from '../utils/roleUtils';
import LOBTreeView from '../components/LOBTreeView';
import LOBImportPanel from '../components/LOBImportPanel';
import { LOBUnitTreeNode } from '../api/lob';
import {
    listFactors,
    createFactor,
    updateFactor,
    deleteFactor,
    validateWeights,
    addGuidance,
    updateGuidance,
    deleteGuidance,
    FactorResponse,
    GuidanceResponse,
    WeightValidationResponse
} from '../api/qualitativeFactors';
import {
    listSections as listScorecardSections,
    createSection as createScorecardSection,
    updateSection as updateScorecardSection,
    deleteSection as deleteScorecardSection,
    createCriterion as createScorecardCriterion,
    updateCriterion as updateScorecardCriterion,
    deleteCriterion as deleteScorecardCriterion,
    getActiveConfigVersion as getScorecardActiveVersion,
    publishConfigVersion as publishScorecardVersion,
    ScorecardSection,
    ScorecardCriterion,
    ScorecardConfigVersion,
} from '../api/scorecard';
import {
    getActiveConfig as getResidualRiskMapConfig,
    listVersions as listResidualRiskMapVersions,
    updateConfig as updateResidualRiskMapConfig,
    ResidualRiskMapResponse,
    DEFAULT_ROW_VALUES,
    DEFAULT_COLUMN_VALUES,
    DEFAULT_RESULT_VALUES,
    getResidualRiskColorClass,
} from '../api/residualRiskMap';

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
    min_days: number | null;
    max_days: number | null;
    downgrade_notches: number | null;  // Scorecard penalty for Final Risk Ranking
    is_system_protected?: boolean;
    created_at: string;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    taxonomy_type: 'standard' | 'bucket';
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
// TYPES - Methodology Library
// ============================================================================

interface Methodology {
    methodology_id: number;
    category_id: number;
    name: string;
    description: string | null;
    variants: string | null;
    sort_order: number;
    is_active: boolean;
}

interface MethodologyCategory {
    category_id: number;
    code: string;
    name: string;
    sort_order: number;
    is_aiml: boolean;
    methodologies: Methodology[];
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

// ============================================================================
// TYPES - Component Definitions
// ============================================================================

interface ComponentDefinition {
    component_id: number;
    section_number: string;
    section_title: string;
    component_code: string;
    component_title: string;
    is_test_or_analysis: boolean;
    expectation_high: string;
    expectation_medium: string;
    expectation_low: string;
    expectation_very_low: string;
    sort_order: number;
    is_active: boolean;
}

interface ComponentConfigurationItem {
    config_item_id: number;
    component_id: number;
    section_number: string;
    section_title: string;
    component_code: string;
    component_title: string;
    expectation_high: string;
    expectation_medium: string;
    expectation_low: string;
    expectation_very_low: string;
}

interface ComponentConfiguration {
    config_id: number;
    config_name: string;
    description: string | null;
    effective_date: string;
    created_by_user_id: number | null;
    created_at: string;
    is_active: boolean;
    config_items?: ComponentConfigurationItem[];
}

export default function TaxonomyPage() {
    // URL search params for direct tab linking
    const [searchParams, setSearchParams] = useSearchParams();
    const { user } = useAuth();
    const canManageTaxonomyFlag = canManageTaxonomy(user);

    // Tab management - initialize from URL param or default to 'general'
    const tabParam = searchParams.get('tab');
    const validTabs = ['general', 'change-type', 'model-type', 'methodology-library', 'kpm', 'fry', 'recommendation-priority', 'risk-factors', 'scorecard', 'residual-risk-map', 'organizations', 'component-definitions'] as const;
    type TabType = typeof validTabs[number];
    const initialTab: TabType = validTabs.includes(tabParam as TabType) ? (tabParam as TabType) : 'general';
    const [activeTab, setActiveTab] = useState<TabType>(initialTab);

    const componentTabParam = searchParams.get('componentTab');
    const validComponentTabs = ['definitions', 'version-history'] as const;
    type ComponentTabType = typeof validComponentTabs[number];
    const initialComponentTab: ComponentTabType = validComponentTabs.includes(componentTabParam as ComponentTabType)
        ? (componentTabParam as ComponentTabType)
        : 'definitions';
    const [componentTab, setComponentTab] = useState<ComponentTabType>(initialComponentTab);

    useEffect(() => {
        const nextTab: TabType = validTabs.includes(tabParam as TabType) ? (tabParam as TabType) : 'general';
        if (nextTab !== activeTab) {
            setActiveTab(nextTab);
        }
    }, [tabParam, activeTab]);

    useEffect(() => {
        const nextComponentTab: ComponentTabType = validComponentTabs.includes(componentTabParam as ComponentTabType)
            ? (componentTabParam as ComponentTabType)
            : 'definitions';
        if (nextComponentTab !== componentTab) {
            setComponentTab(nextComponentTab);
        }
    }, [componentTabParam, componentTab]);

    // Update URL when tab changes
    const handleTabChange = (tab: TabType) => {
        setActiveTab(tab);
        if (tab === 'general') {
            searchParams.delete('tab');
        } else {
            searchParams.set('tab', tab);
        }
        if (tab !== 'component-definitions') {
            searchParams.delete('componentTab');
        }
        setSearchParams(searchParams, { replace: true });
    };

    const handleComponentTabChange = (tab: ComponentTabType) => {
        setComponentTab(tab);
        if (tab === 'definitions') {
            searchParams.delete('componentTab');
        } else {
            searchParams.set('componentTab', tab);
        }
        setSearchParams(searchParams, { replace: true });
    };

    // Recommendation Priority Config state
    const [priorityConfigs, setPriorityConfigs] = useState<RecommendationPriorityConfig[]>([]);
    const [priorityConfigLoading, setPriorityConfigLoading] = useState(false);
    const [priorityConfigError, setPriorityConfigError] = useState<string | null>(null);
    const [editingPriorityConfig, setEditingPriorityConfig] = useState<RecommendationPriorityConfig | null>(null);

    // Timeframe Config state
    const [timeframeConfigs, setTimeframeConfigs] = useState<any[]>([]);
    const [timeframeConfigsLoading, setTimeframeConfigsLoading] = useState(false);
    const [showTimeframeSection, setShowTimeframeSection] = useState(true);
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

    // Risk Factors state
    const [riskFactors, setRiskFactors] = useState<FactorResponse[]>([]);
    const [riskFactorsLoading, setRiskFactorsLoading] = useState(false);
    const [riskFactorsError, setRiskFactorsError] = useState<string | null>(null);
    const [selectedFactor, setSelectedFactor] = useState<FactorResponse | null>(null);
    const [showFactorForm, setShowFactorForm] = useState(false);
    const [editingFactor, setEditingFactor] = useState<FactorResponse | null>(null);
    const [factorFormData, setFactorFormData] = useState({
        code: '',
        name: '',
        description: '',
        weight: 0.25,
        sort_order: 0
    });
    const [showGuidanceForm, setShowGuidanceForm] = useState(false);
    const [editingGuidance, setEditingGuidance] = useState<GuidanceResponse | null>(null);
    const [guidanceFormData, setGuidanceFormData] = useState({
        rating: 'MEDIUM' as 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_HIGH' | 'VERY_LOW',
        points: 2,
        description: '',
        sort_order: 0
    });
    const [weightValidation, setWeightValidation] = useState<WeightValidationResponse | null>(null);

    // Scorecard configuration state
    const [scorecardSections, setScorecardSections] = useState<ScorecardSection[]>([]);
    const [scorecardLoading, setScorecardLoading] = useState(false);
    const [scorecardError, setScorecardError] = useState<string | null>(null);
    const [selectedScorecardSection, setSelectedScorecardSection] = useState<ScorecardSection | null>(null);
    const [showScorecardSectionForm, setShowScorecardSectionForm] = useState(false);
    const [editingScorecardSection, setEditingScorecardSection] = useState<ScorecardSection | null>(null);
    const [scorecardSectionFormData, setScorecardSectionFormData] = useState({
        code: '',
        name: '',
        description: '',
        sort_order: 0,
        is_active: true
    });
    const [showScorecardCriterionForm, setShowScorecardCriterionForm] = useState(false);
    const [editingScorecardCriterion, setEditingScorecardCriterion] = useState<ScorecardCriterion | null>(null);
    const [scorecardCriterionFormData, setScorecardCriterionFormData] = useState({
        code: '',
        name: '',
        description_prompt: '',
        comments_prompt: '',
        include_in_summary: true,
        allow_zero: true,
        weight: 1.0,
        sort_order: 0,
        is_active: true
    });

    // Scorecard version state
    const [scorecardActiveVersion, setScorecardActiveVersion] = useState<ScorecardConfigVersion | null>(null);
    const [showScorecardPublishModal, setShowScorecardPublishModal] = useState(false);
    const [scorecardPublishForm, setScorecardPublishForm] = useState({
        version_name: '',
        description: ''
    });
    const [scorecardPublishing, setScorecardPublishing] = useState(false);

    // Residual Risk Map state
    const [residualRiskMapConfig, setResidualRiskMapConfig] = useState<ResidualRiskMapResponse | null>(null);
    const [residualRiskMapVersions, setResidualRiskMapVersions] = useState<ResidualRiskMapResponse[]>([]);
    const [residualRiskMapLoading, setResidualRiskMapLoading] = useState(false);
    const [residualRiskMapError, setResidualRiskMapError] = useState<string | null>(null);
    const [showResidualRiskMapEditor, setShowResidualRiskMapEditor] = useState(false);
    const [residualRiskMapEditMatrix, setResidualRiskMapEditMatrix] = useState<Record<string, Record<string, string>>>({});
    const [residualRiskMapSaving, setResidualRiskMapSaving] = useState(false);
    const [residualRiskMapPublishForm, setResidualRiskMapPublishForm] = useState({
        version_name: '',
        description: ''
    });

    // LOB (Organization Hierarchy) state
    const [selectedLOB, setSelectedLOB] = useState<LOBUnitTreeNode | null>(null);

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
        is_active: true,
        min_days: null as number | null,
        max_days: null as number | null,
        downgrade_notches: null as number | null
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

    // Methodology library state
    const [methodologyCategories, setMethodologyCategories] = useState<MethodologyCategory[]>([]);
    const [selectedMethodologyCategory, setSelectedMethodologyCategory] = useState<MethodologyCategory | null>(null);
    const [expandedMethodologyCategories, setExpandedMethodologyCategories] = useState<Set<number>>(new Set());
    const [showMethodologyCategoryForm, setShowMethodologyCategoryForm] = useState(false);
    const [showMethodologyForm, setShowMethodologyForm] = useState(false);
    const [editingMethodology, setEditingMethodology] = useState<Methodology | null>(null);
    const [editingMethodologyCategory, setEditingMethodologyCategory] = useState<MethodologyCategory | null>(null);
    const [methodologyCategoryFormData, setMethodologyCategoryFormData] = useState({
        code: '',
        name: '',
        sort_order: 0,
        is_aiml: false
    });
    const [methodologyFormData, setMethodologyFormData] = useState({
        category_id: 0,
        name: '',
        description: '',
        variants: '',
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

    // Component Definitions state
    const [componentDefinitions, setComponentDefinitions] = useState<ComponentDefinition[]>([]);
    const [activeComponentConfig, setActiveComponentConfig] = useState<ComponentConfiguration | null>(null);
    const [editingComponentId, setEditingComponentId] = useState<number | null>(null);
    const [componentEditForm, setComponentEditForm] = useState<Partial<ComponentDefinition>>({});
    const [componentDefLoading, setComponentDefLoading] = useState(false);
    const [componentDefError, setComponentDefError] = useState<string | null>(null);
    const [componentDefSuccess, setComponentDefSuccess] = useState<string | null>(null);
    const [showComponentPublishModal, setShowComponentPublishModal] = useState(false);
    const [componentPublishForm, setComponentPublishForm] = useState({
        config_name: '',
        description: '',
        effective_date: new Date().toISOString().split('T')[0]
    });
    const [componentConfigHistory, setComponentConfigHistory] = useState<ComponentConfiguration[]>([]);
    const [componentConfigHistoryLoading, setComponentConfigHistoryLoading] = useState(false);
    const [componentConfigHistoryError, setComponentConfigHistoryError] = useState<string | null>(null);
    const [expandedComponentConfigId, setExpandedComponentConfigId] = useState<number | null>(null);
    const [expandedComponentConfig, setExpandedComponentConfig] = useState<ComponentConfiguration | null>(null);
    const [componentConfigDetailLoading, setComponentConfigDetailLoading] = useState(false);

    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (activeTab === 'general') {
            fetchTaxonomies();
        } else if (activeTab === 'change-type') {
            fetchChangeCategories();
        } else if (activeTab === 'model-type') {
            fetchModelCategories();
        } else if (activeTab === 'methodology-library') {
            fetchMethodologyCategories();
        } else if (activeTab === 'kpm') {
            fetchKpmCategories();
        } else if (activeTab === 'fry') {
            fetchFryReports();
        } else if (activeTab === 'recommendation-priority') {
            fetchPriorityConfigs();
            fetchTimeframeConfigs(); // Timeframe section is expanded by default
        } else if (activeTab === 'risk-factors') {
            fetchRiskFactors();
        } else if (activeTab === 'scorecard') {
            fetchScorecardSections();
        } else if (activeTab === 'residual-risk-map') {
            fetchResidualRiskMapConfig();
        } else if (activeTab === 'component-definitions') {
            fetchComponentDefinitions();
        }
    }, [activeTab]);

    useEffect(() => {
        if (activeTab === 'component-definitions' && componentTab === 'version-history') {
            fetchComponentDefinitionHistory();
        }
    }, [activeTab, componentTab]);

    // ============================================================================
    // COMPONENT DEFINITIONS FUNCTIONS
    // ============================================================================

    const fetchComponentDefinitions = async () => {
        setComponentDefLoading(true);
        setComponentDefError(null);
        try {
            // Fetch component definitions
            const componentsRes = await api.get('/validation-workflow/component-definitions');
            setComponentDefinitions(componentsRes.data);

            // Fetch configurations to get active one
            const configsRes = await api.get('/validation-workflow/configurations');
            const activeConf = configsRes.data.find((c: ComponentConfiguration) => c.is_active);
            setActiveComponentConfig(activeConf || null);
        } catch (err: any) {
            setComponentDefError(err.response?.data?.detail || 'Failed to load component definitions');
            console.error('Error loading component definitions:', err);
        } finally {
            setComponentDefLoading(false);
            setLoading(false);
        }
    };

    const fetchComponentDefinitionHistory = async () => {
        setComponentConfigHistoryLoading(true);
        setComponentConfigHistoryError(null);
        try {
            const response = await api.get('/validation-workflow/configurations');
            setComponentConfigHistory(response.data);
        } catch (err: any) {
            setComponentConfigHistoryError(err.response?.data?.detail || 'Failed to fetch configuration history');
        } finally {
            setComponentConfigHistoryLoading(false);
        }
    };

    const handleExpandComponentConfiguration = async (configId: number) => {
        if (expandedComponentConfigId === configId) {
            setExpandedComponentConfigId(null);
            setExpandedComponentConfig(null);
            return;
        }

        setExpandedComponentConfigId(configId);
        setExpandedComponentConfig(null);
        setComponentConfigDetailLoading(true);
        setComponentConfigHistoryError(null);
        try {
            const response = await api.get(`/validation-workflow/configurations/${configId}`);
            setExpandedComponentConfig(response.data);
        } catch (err: any) {
            setComponentConfigHistoryError(err.response?.data?.detail || 'Failed to fetch configuration details');
        } finally {
            setComponentConfigDetailLoading(false);
        }
    };

    const handleComponentEditClick = (component: ComponentDefinition) => {
        setEditingComponentId(component.component_id);
        setComponentEditForm({
            expectation_high: component.expectation_high,
            expectation_medium: component.expectation_medium,
            expectation_low: component.expectation_low,
            expectation_very_low: component.expectation_very_low
        });
    };

    const handleComponentCancelEdit = () => {
        setEditingComponentId(null);
        setComponentEditForm({});
    };

    const handleComponentSaveEdit = async (componentId: number) => {
        setComponentDefLoading(true);
        setComponentDefError(null);
        setComponentDefSuccess(null);

        try {
            const response = await api.patch(
                `/validation-workflow/component-definitions/${componentId}`,
                componentEditForm
            );

            // Update local state
            setComponentDefinitions(componentDefinitions.map(c =>
                c.component_id === componentId ? response.data : c
            ));

            setEditingComponentId(null);
            setComponentEditForm({});
            setComponentDefSuccess('Component updated successfully. Changes will apply to new plans after publishing a new configuration.');
        } catch (err: any) {
            setComponentDefError(err.response?.data?.detail || 'Failed to update component');
            console.error('Error updating component:', err);
        } finally {
            setComponentDefLoading(false);
        }
    };

    const handleComponentPublishConfiguration = async () => {
        setComponentDefLoading(true);
        setComponentDefError(null);
        setComponentDefSuccess(null);

        try {
            const response = await api.post('/validation-workflow/configurations/publish', componentPublishForm);

            setActiveComponentConfig(response.data);
            setShowComponentPublishModal(false);
            setComponentPublishForm({
                config_name: '',
                description: '',
                effective_date: new Date().toISOString().split('T')[0]
            });
            setComponentDefSuccess(`Configuration "${response.data.config_name}" published successfully. New validation plans will use this configuration.`);
            await fetchComponentDefinitionHistory();
        } catch (err: any) {
            setComponentDefError(err.response?.data?.detail || 'Failed to publish configuration');
            console.error('Error publishing configuration:', err);
        } finally {
            setComponentDefLoading(false);
        }
    };

    // ============================================================================
    // RESIDUAL RISK MAP FUNCTIONS
    // ============================================================================

    const fetchResidualRiskMapConfig = async () => {
        setResidualRiskMapLoading(true);
        setResidualRiskMapError(null);
        try {
            const config = await getResidualRiskMapConfig();
            setResidualRiskMapConfig(config);
            // Also fetch version history
            const versions = await listResidualRiskMapVersions();
            setResidualRiskMapVersions(versions);
        } catch (error: any) {
            console.error('Failed to fetch residual risk map:', error);
            if (error.response?.status === 404) {
                // No config exists yet, use default
                setResidualRiskMapConfig(null);
            } else {
                setResidualRiskMapError('Failed to load residual risk map configuration');
            }
        } finally {
            setResidualRiskMapLoading(false);
        }
    };

    const startEditResidualRiskMap = () => {
        if (residualRiskMapConfig) {
            // Clone the current matrix for editing
            const matrixCopy: Record<string, Record<string, string>> = {};
            const currentMatrix = residualRiskMapConfig.matrix_config.matrix;
            for (const rowKey of Object.keys(currentMatrix)) {
                matrixCopy[rowKey] = { ...currentMatrix[rowKey] };
            }
            setResidualRiskMapEditMatrix(matrixCopy);
        } else {
            // Initialize with defaults
            const defaultMatrix: Record<string, Record<string, string>> = {};
            for (const row of DEFAULT_ROW_VALUES) {
                defaultMatrix[row] = {};
                for (const col of DEFAULT_COLUMN_VALUES) {
                    defaultMatrix[row][col] = 'Medium'; // Default value
                }
            }
            setResidualRiskMapEditMatrix(defaultMatrix);
        }
        setShowResidualRiskMapEditor(true);
    };

    const handleResidualRiskMapCellChange = (row: string, col: string, value: string) => {
        setResidualRiskMapEditMatrix(prev => ({
            ...prev,
            [row]: {
                ...prev[row],
                [col]: value
            }
        }));
    };

    const handleSaveResidualRiskMap = async (e: React.FormEvent) => {
        e.preventDefault();
        setResidualRiskMapSaving(true);
        try {
            const updateData = {
                matrix_config: {
                    row_axis_label: 'Inherent Risk Tier',
                    column_axis_label: 'Scorecard Outcome',
                    row_values: DEFAULT_ROW_VALUES,
                    column_values: DEFAULT_COLUMN_VALUES,
                    result_values: DEFAULT_RESULT_VALUES,
                    matrix: residualRiskMapEditMatrix
                },
                version_name: residualRiskMapPublishForm.version_name || undefined,
                description: residualRiskMapPublishForm.description || undefined
            };
            await updateResidualRiskMapConfig(updateData);
            setShowResidualRiskMapEditor(false);
            setResidualRiskMapPublishForm({ version_name: '', description: '' });
            await fetchResidualRiskMapConfig();
        } catch (error) {
            console.error('Failed to save residual risk map:', error);
            setResidualRiskMapError('Failed to save residual risk map configuration');
        } finally {
            setResidualRiskMapSaving(false);
        }
    };

    const cancelEditResidualRiskMap = () => {
        setShowResidualRiskMapEditor(false);
        setResidualRiskMapEditMatrix({});
        setResidualRiskMapPublishForm({ version_name: '', description: '' });
    };

    // ============================================================================
    // RISK FACTOR FUNCTIONS
    // ============================================================================

    const fetchRiskFactors = async () => {
        setRiskFactorsLoading(true);
        setRiskFactorsError(null);
        try {
            const factors = await listFactors(true); // Include inactive
            setRiskFactors(factors);
            if (factors.length > 0 && !selectedFactor) {
                setSelectedFactor(factors[0]);
            }
            // Validate weights
            const validation = await validateWeights();
            setWeightValidation(validation);
        } catch (error) {
            console.error('Failed to fetch risk factors:', error);
            setRiskFactorsError('Failed to load risk factors');
        } finally {
            setRiskFactorsLoading(false);
        }
    };

    const resetFactorForm = () => {
        setFactorFormData({
            code: '',
            name: '',
            description: '',
            weight: 0.25,
            sort_order: 0
        });
        setShowFactorForm(false);
        setEditingFactor(null);
    };

    const resetGuidanceForm = () => {
        setGuidanceFormData({
            rating: 'MEDIUM',
            points: 2,
            description: '',
            sort_order: 0
        });
        setShowGuidanceForm(false);
        setEditingGuidance(null);
    };

    const handleCreateFactor = async () => {
        try {
            await createFactor({
                code: factorFormData.code,
                name: factorFormData.name,
                description: factorFormData.description || undefined,
                weight: factorFormData.weight,
                sort_order: factorFormData.sort_order
            });
            resetFactorForm();
            fetchRiskFactors();
        } catch (error) {
            console.error('Failed to create factor:', error);
            setRiskFactorsError('Failed to create factor');
        }
    };

    const handleUpdateFactor = async () => {
        if (!editingFactor) return;
        try {
            await updateFactor(editingFactor.factor_id, {
                code: factorFormData.code,
                name: factorFormData.name,
                description: factorFormData.description || undefined,
                weight: factorFormData.weight,
                sort_order: factorFormData.sort_order
            });
            resetFactorForm();
            fetchRiskFactors();
        } catch (error) {
            console.error('Failed to update factor:', error);
            setRiskFactorsError('Failed to update factor');
        }
    };

    const handleDeleteFactor = async (factorId: number) => {
        if (!confirm('Are you sure you want to deactivate this factor?')) return;
        try {
            await deleteFactor(factorId);
            fetchRiskFactors();
            if (selectedFactor?.factor_id === factorId) {
                setSelectedFactor(null);
            }
        } catch (error) {
            console.error('Failed to delete factor:', error);
            setRiskFactorsError('Failed to deactivate factor');
        }
    };

    const handleCreateGuidance = async () => {
        if (!selectedFactor) return;
        try {
            await addGuidance(selectedFactor.factor_id, {
                rating: guidanceFormData.rating,
                points: guidanceFormData.points,
                description: guidanceFormData.description,
                sort_order: guidanceFormData.sort_order
            });
            resetGuidanceForm();
            fetchRiskFactors();
        } catch (error) {
            console.error('Failed to create guidance:', error);
            setRiskFactorsError('Failed to create guidance');
        }
    };

    const handleUpdateGuidance = async () => {
        if (!editingGuidance) return;
        try {
            await updateGuidance(editingGuidance.guidance_id, {
                rating: guidanceFormData.rating,
                points: guidanceFormData.points,
                description: guidanceFormData.description,
                sort_order: guidanceFormData.sort_order
            });
            resetGuidanceForm();
            fetchRiskFactors();
        } catch (error) {
            console.error('Failed to update guidance:', error);
            setRiskFactorsError('Failed to update guidance');
        }
    };

    const handleDeleteGuidance = async (guidanceId: number) => {
        if (!confirm('Are you sure you want to delete this guidance?')) return;
        try {
            await deleteGuidance(guidanceId);
            fetchRiskFactors();
        } catch (error) {
            console.error('Failed to delete guidance:', error);
            setRiskFactorsError('Failed to delete guidance');
        }
    };

    const startEditFactor = (factor: FactorResponse) => {
        setEditingFactor(factor);
        setFactorFormData({
            code: factor.code,
            name: factor.name,
            description: factor.description || '',
            weight: factor.weight,
            sort_order: factor.sort_order
        });
        setShowFactorForm(true);
    };

    const startEditGuidance = (guidance: GuidanceResponse) => {
        setEditingGuidance(guidance);
        setGuidanceFormData({
            rating: guidance.rating as 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_HIGH' | 'VERY_LOW',
            points: guidance.points,
            description: guidance.description,
            sort_order: guidance.sort_order
        });
        setShowGuidanceForm(true);
    };

    // ============================================================================
    // SCORECARD FUNCTIONS
    // ============================================================================

    const fetchScorecardSections = async () => {
        setScorecardLoading(true);
        setScorecardError(null);
        try {
            // Fetch sections and active version in parallel
            const [sections, activeVersion] = await Promise.all([
                listScorecardSections(true), // Include inactive
                getScorecardActiveVersion()
            ]);
            setScorecardSections(sections);
            setScorecardActiveVersion(activeVersion);
            if (sections.length > 0 && !selectedScorecardSection) {
                setSelectedScorecardSection(sections[0]);
            }
        } catch (error) {
            console.error('Failed to fetch scorecard sections:', error);
            setScorecardError('Failed to load scorecard configuration');
        } finally {
            setScorecardLoading(false);
        }
    };

    const handlePublishScorecardVersion = async (e: React.FormEvent) => {
        e.preventDefault();
        setScorecardPublishing(true);
        try {
            await publishScorecardVersion({
                version_name: scorecardPublishForm.version_name || undefined,
                description: scorecardPublishForm.description || undefined
            });
            setShowScorecardPublishModal(false);
            setScorecardPublishForm({ version_name: '', description: '' });
            // Refresh to get the new active version
            await fetchScorecardSections();
        } catch (error) {
            console.error('Failed to publish scorecard version:', error);
            setScorecardError('Failed to publish new version');
        } finally {
            setScorecardPublishing(false);
        }
    };

    const resetScorecardSectionForm = () => {
        setScorecardSectionFormData({
            code: '',
            name: '',
            description: '',
            sort_order: scorecardSections.length,
            is_active: true
        });
        setEditingScorecardSection(null);
    };

    const handleScorecardSectionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingScorecardSection) {
                const updated = await updateScorecardSection(editingScorecardSection.section_id, {
                    name: scorecardSectionFormData.name,
                    description: scorecardSectionFormData.description || null,
                    sort_order: scorecardSectionFormData.sort_order,
                    is_active: scorecardSectionFormData.is_active
                });
                setScorecardSections(prev => prev.map(s => s.section_id === updated.section_id ? { ...s, ...updated } : s));
                if (selectedScorecardSection?.section_id === updated.section_id) {
                    setSelectedScorecardSection({ ...selectedScorecardSection, ...updated });
                }
                // Refresh active version to update has_unpublished_changes flag
                const activeVersion = await getScorecardActiveVersion();
                setScorecardActiveVersion(activeVersion);
            } else {
                await createScorecardSection({
                    code: scorecardSectionFormData.code,
                    name: scorecardSectionFormData.name,
                    description: scorecardSectionFormData.description || undefined,
                    sort_order: scorecardSectionFormData.sort_order,
                    is_active: scorecardSectionFormData.is_active
                });
                // Refresh to get full section with criteria
                await fetchScorecardSections();
            }
            setShowScorecardSectionForm(false);
            resetScorecardSectionForm();
        } catch (error: any) {
            console.error('Failed to save section:', error);
            setScorecardError(error.response?.data?.detail || 'Failed to save section');
        }
    };

    const handleDeleteScorecardSection = async (sectionId: number) => {
        if (!confirm('Delete this section? All criteria in this section will also be deleted.')) return;
        try {
            await deleteScorecardSection(sectionId);
            setScorecardSections(prev => prev.filter(s => s.section_id !== sectionId));
            if (selectedScorecardSection?.section_id === sectionId) {
                setSelectedScorecardSection(scorecardSections.find(s => s.section_id !== sectionId) || null);
            }
            // Refresh active version to update has_unpublished_changes flag
            const activeVersion = await getScorecardActiveVersion();
            setScorecardActiveVersion(activeVersion);
        } catch (error: any) {
            console.error('Failed to delete section:', error);
            setScorecardError(error.response?.data?.detail || 'Failed to delete section');
        }
    };

    const startEditScorecardSection = (section: ScorecardSection) => {
        setEditingScorecardSection(section);
        setScorecardSectionFormData({
            code: section.code,
            name: section.name,
            description: section.description || '',
            sort_order: section.sort_order,
            is_active: section.is_active
        });
        setShowScorecardSectionForm(true);
    };

    const resetScorecardCriterionForm = () => {
        setScorecardCriterionFormData({
            code: '',
            name: '',
            description_prompt: '',
            comments_prompt: '',
            include_in_summary: true,
            allow_zero: true,
            weight: 1.0,
            sort_order: selectedScorecardSection?.criteria?.length || 0,
            is_active: true
        });
        setEditingScorecardCriterion(null);
    };

    const handleScorecardCriterionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedScorecardSection) return;

        try {
            if (editingScorecardCriterion) {
                const updated = await updateScorecardCriterion(editingScorecardCriterion.criterion_id, {
                    name: scorecardCriterionFormData.name,
                    description_prompt: scorecardCriterionFormData.description_prompt || null,
                    comments_prompt: scorecardCriterionFormData.comments_prompt || null,
                    include_in_summary: scorecardCriterionFormData.include_in_summary,
                    allow_zero: scorecardCriterionFormData.allow_zero,
                    weight: scorecardCriterionFormData.weight,
                    sort_order: scorecardCriterionFormData.sort_order,
                    is_active: scorecardCriterionFormData.is_active
                });
                // Update criteria in the section
                setSelectedScorecardSection(prev => {
                    if (!prev) return prev;
                    return {
                        ...prev,
                        criteria: prev.criteria.map(c =>
                            c.criterion_id === updated.criterion_id ? updated : c
                        )
                    };
                });
                setScorecardSections(prev => prev.map(s => {
                    if (s.section_id === selectedScorecardSection.section_id) {
                        return {
                            ...s,
                            criteria: s.criteria.map(c =>
                                c.criterion_id === updated.criterion_id ? updated : c
                            )
                        };
                    }
                    return s;
                }));
            } else {
                const created = await createScorecardCriterion({
                    code: scorecardCriterionFormData.code,
                    section_id: selectedScorecardSection.section_id,
                    name: scorecardCriterionFormData.name,
                    description_prompt: scorecardCriterionFormData.description_prompt || undefined,
                    comments_prompt: scorecardCriterionFormData.comments_prompt || undefined,
                    include_in_summary: scorecardCriterionFormData.include_in_summary,
                    allow_zero: scorecardCriterionFormData.allow_zero,
                    weight: scorecardCriterionFormData.weight,
                    sort_order: scorecardCriterionFormData.sort_order,
                    is_active: scorecardCriterionFormData.is_active
                });
                // Add to section
                setSelectedScorecardSection(prev => {
                    if (!prev) return prev;
                    return {
                        ...prev,
                        criteria: [...prev.criteria, created]
                    };
                });
                setScorecardSections(prev => prev.map(s => {
                    if (s.section_id === selectedScorecardSection.section_id) {
                        return {
                            ...s,
                            criteria: [...s.criteria, created]
                        };
                    }
                    return s;
                }));
            }

            // Refresh active version to update has_unpublished_changes flag
            const activeVersion = await getScorecardActiveVersion();
            setScorecardActiveVersion(activeVersion);

            setShowScorecardCriterionForm(false);
            resetScorecardCriterionForm();
        } catch (error: any) {
            console.error('Failed to save criterion:', error);
            setScorecardError(error.response?.data?.detail || 'Failed to save criterion');
        }
    };

    const handleDeleteScorecardCriterion = async (criterionId: number) => {
        if (!confirm('Delete this criterion? Existing ratings will be preserved but orphaned.')) return;
        if (!selectedScorecardSection) return;

        try {
            await deleteScorecardCriterion(criterionId);
            setSelectedScorecardSection(prev => {
                if (!prev) return prev;
                return {
                    ...prev,
                    criteria: prev.criteria.filter(c => c.criterion_id !== criterionId)
                };
            });
            setScorecardSections(prev => prev.map(s => {
                if (s.section_id === selectedScorecardSection.section_id) {
                    return {
                        ...s,
                        criteria: s.criteria.filter(c => c.criterion_id !== criterionId)
                    };
                }
                return s;
            }));

            // Refresh active version to update has_unpublished_changes flag
            const activeVersion = await getScorecardActiveVersion();
            setScorecardActiveVersion(activeVersion);
        } catch (error: any) {
            console.error('Failed to delete criterion:', error);
            setScorecardError(error.response?.data?.detail || 'Failed to delete criterion');
        }
    };

    const startEditScorecardCriterion = (criterion: ScorecardCriterion) => {
        setEditingScorecardCriterion(criterion);
        setScorecardCriterionFormData({
            code: criterion.code,
            name: criterion.name,
            description_prompt: criterion.description_prompt || '',
            comments_prompt: criterion.comments_prompt || '',
            include_in_summary: criterion.include_in_summary,
            allow_zero: criterion.allow_zero,
            weight: criterion.weight,
            sort_order: criterion.sort_order,
            is_active: criterion.is_active
        });
        setShowScorecardCriterionForm(true);
    };

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
            is_active: true,
            min_days: null,
            max_days: null,
            downgrade_notches: null
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
            is_active: value.is_active,
            min_days: value.min_days,
            max_days: value.max_days,
            downgrade_notches: value.downgrade_notches
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

    const isMonitoringCategoryValue = (value: TaxonomyValue): boolean => {
        if (selectedTaxonomy?.name !== 'Recommendation Category') return false;
        return value.code === 'MONITORING' || value.label === 'Monitoring';
    };

    const isDeleteProtectedValue = (value: TaxonomyValue): boolean => {
        return isMonitoringCategoryValue(value)
            || !!value.is_system_protected
            || (selectedTaxonomy?.name === 'Validation Type' && value.code === 'TARGETED');
    };

    const isDeactivationProtectedValue = (value: TaxonomyValue): boolean => {
        return isMonitoringCategoryValue(value) || !!value.is_system_protected;
    };

    const isEditingDeactivationProtected = editingValue
        ? isDeactivationProtectedValue(editingValue)
        : false;
    const disableActiveToggle = isEditingDeactivationProtected && valueFormData.is_active;

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
    // METHODOLOGY LIBRARY FUNCTIONS
    // ============================================================================

    const fetchMethodologyCategories = async () => {
        try {
            const response = await api.get('/methodology-library/categories');
            setMethodologyCategories(response.data);
            if (response.data.length > 0 && !selectedMethodologyCategory) {
                setSelectedMethodologyCategory(response.data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch methodology categories:', error);
        } finally {
            setLoading(false);
        }
    };

    const toggleMethodologyCategory = (categoryId: number) => {
        setExpandedMethodologyCategories(prev => {
            const newSet = new Set(prev);
            if (newSet.has(categoryId)) {
                newSet.delete(categoryId);
            } else {
                newSet.add(categoryId);
            }
            return newSet;
        });
    };

    const resetMethodologyCategoryForm = () => {
        setMethodologyCategoryFormData({ code: '', name: '', sort_order: 0, is_aiml: false });
        setEditingMethodologyCategory(null);
        setShowMethodologyCategoryForm(false);
    };

    const resetMethodologyForm = () => {
        setMethodologyFormData({
            category_id: 0,
            name: '',
            description: '',
            variants: '',
            sort_order: 0,
            is_active: true
        });
        setEditingMethodology(null);
        setShowMethodologyForm(false);
    };

    const handleMethodologyCategorySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingMethodologyCategory) {
                await api.patch(`/methodology-library/categories/${editingMethodologyCategory.category_id}`, methodologyCategoryFormData);
            } else {
                await api.post('/methodology-library/categories', methodologyCategoryFormData);
            }
            resetMethodologyCategoryForm();
            fetchMethodologyCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save category');
            console.error('Failed to save category:', error);
        }
    };

    const handleEditMethodologyCategory = (category: MethodologyCategory) => {
        setEditingMethodologyCategory(category);
        setMethodologyCategoryFormData({
            code: category.code,
            name: category.name,
            sort_order: category.sort_order,
            is_aiml: category.is_aiml
        });
        setShowMethodologyCategoryForm(true);
    };

    const handleMethodologySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingMethodology) {
                await api.patch(`/methodology-library/methodologies/${editingMethodology.methodology_id}`, methodologyFormData);
            } else {
                await api.post('/methodology-library/methodologies', methodologyFormData);
            }
            resetMethodologyForm();
            fetchMethodologyCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save methodology');
            console.error('Failed to save methodology:', error);
        }
    };

    const handleEditMethodology = (methodology: Methodology, categoryId: number) => {
        setEditingMethodology(methodology);
        setMethodologyFormData({
            category_id: categoryId,
            name: methodology.name,
            description: methodology.description || '',
            variants: methodology.variants || '',
            sort_order: methodology.sort_order,
            is_active: methodology.is_active
        });
        setShowMethodologyForm(true);
    };

    const handleAddMethodologyToCategory = (categoryId: number) => {
        setMethodologyFormData({
            category_id: categoryId,
            name: '',
            description: '',
            variants: '',
            sort_order: 0,
            is_active: true
        });
        setEditingMethodology(null);
        setShowMethodologyForm(true);
    };

    const handleToggleMethodologyActive = async (methodology: Methodology) => {
        try {
            await api.patch(`/methodology-library/methodologies/${methodology.methodology_id}`, {
                is_active: !methodology.is_active
            });
            fetchMethodologyCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to update methodology status');
            console.error('Failed to toggle methodology status:', error);
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

    // ============================================================================
    // COMPONENT DEFINITIONS HELPER FUNCTIONS
    // ============================================================================

    const getExpectationBadge = (expectation: string) => {
        const colors: Record<string, string> = {
            'Required': 'bg-green-100 text-green-800',
            'IfApplicable': 'bg-yellow-100 text-yellow-800',
            'NotExpected': 'bg-gray-100 text-gray-800'
        };
        return colors[expectation] || 'bg-gray-100 text-gray-800';
    };

    const formatExpectation = (expectation: string) => {
        switch (expectation) {
            case 'IfApplicable':
                return 'If Applicable';
            case 'NotExpected':
                return 'Not Expected';
            default:
                return expectation;
        }
    };

    const groupComponentConfigItemsBySection = (items: ComponentConfigurationItem[]) => {
        const grouped: Record<string, ComponentConfigurationItem[]> = {};
        items.forEach(item => {
            const key = `${item.section_number}|${item.section_title}`;
            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(item);
        });
        return grouped;
    };

    // Group components by section for display
    const groupedComponents = componentDefinitions.reduce((acc, comp) => {
        const sectionKey = `${comp.section_number}|${comp.section_title}`;
        if (!acc[sectionKey]) {
            acc[sectionKey] = [];
        }
        acc[sectionKey].push(comp);
        return acc;
    }, {} as Record<string, ComponentDefinition[]>);

    // Sort sections by section number
    const sections = Object.keys(groupedComponents).sort((a, b) => {
        const aNum = parseInt(a.split('|')[0]);
        const bNum = parseInt(b.split('|')[0]);
        return aNum - bNum;
    });

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

            {/* Tab Selector - Dropdown */}
            <div className="mb-6">
                <div className="flex items-center gap-4">
                    <label htmlFor="taxonomy-tab-select" className="text-sm font-medium text-gray-700">
                        Configuration Section:
                    </label>
                    <select
                        id="taxonomy-tab-select"
                        value={activeTab}
                        onChange={(e) => handleTabChange(e.target.value as TabType)}
                        className="block w-72 px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                    >
                        <option value="general">General Taxonomies</option>
                        <option value="change-type">Change Type Taxonomy</option>
                        <option value="model-type">Model Type Taxonomy</option>
                        <option value="methodology-library">Methodology Library</option>
                        <option value="kpm">KPM Library</option>
                        <option value="fry">FRY 14 Config</option>
                        <option value="recommendation-priority">Priority Workflow Config</option>
                        <option value="risk-factors">Risk Factors</option>
                        <option value="scorecard">Scorecard Config</option>
                        <option value="residual-risk-map">Residual Risk Map</option>
                        <option value="organizations">Organizations (LOB)</option>
                        <option value="component-definitions">Validation Component Definitions</option>
                    </select>
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
                                                {selectedTaxonomy.taxonomy_type === 'bucket' && (
                                                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                                        Bucket Taxonomy
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
                                                {/* Bucket range fields - only for bucket taxonomies */}
                                                {selectedTaxonomy.taxonomy_type === 'bucket' && (
                                                    <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <span className="text-sm font-medium text-blue-800">Range (Days)</span>
                                                            {!canManageTaxonomyFlag && (
                                                                <span className="text-xs text-blue-600">(Admin only)</span>
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-blue-600 mb-3">
                                                            Leave Min empty for "≤ Max" (first bucket). Leave Max empty for "≥ Min" (last bucket).
                                                        </p>
                                                        <div className="grid grid-cols-2 gap-4">
                                                            <div>
                                                                <label htmlFor="val_min_days" className="block text-sm font-medium mb-1">
                                                                    Min Days
                                                                </label>
                                                                <input
                                                                    id="val_min_days"
                                                                    type="number"
                                                                    className={`input-field ${!canManageTaxonomyFlag ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                                                    value={valueFormData.min_days ?? ''}
                                                                    onChange={(e) => setValueFormData({
                                                                        ...valueFormData,
                                                                        min_days: e.target.value === '' ? null : parseInt(e.target.value)
                                                                    })}
                                                                    disabled={!canManageTaxonomyFlag}
                                                                    placeholder="null (unbounded)"
                                                                />
                                                            </div>
                                                            <div>
                                                                <label htmlFor="val_max_days" className="block text-sm font-medium mb-1">
                                                                    Max Days
                                                                </label>
                                                                <input
                                                                    id="val_max_days"
                                                                    type="number"
                                                                    className={`input-field ${!canManageTaxonomyFlag ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                                                    value={valueFormData.max_days ?? ''}
                                                                    onChange={(e) => setValueFormData({
                                                                        ...valueFormData,
                                                                        max_days: e.target.value === '' ? null : parseInt(e.target.value)
                                                                    })}
                                                                    disabled={!canManageTaxonomyFlag}
                                                                    placeholder="null (unbounded)"
                                                                />
                                                            </div>
                                                        </div>
                                                        {/* Downgrade notches for Final Risk Ranking */}
                                                        <div className="mt-4 pt-3 border-t border-blue-200">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <span className="text-sm font-medium text-blue-800">Scorecard Downgrade</span>
                                                                <span className="text-xs text-blue-600">(for Final Risk Ranking)</span>
                                                            </div>
                                                            <p className="text-xs text-blue-600 mb-3">
                                                                Number of notches to downgrade the scorecard outcome when a model falls in this past-due bucket.
                                                                Green → Green- → Yellow+ → Yellow → Yellow- → Red (capped at Red).
                                                            </p>
                                                            <div className="w-1/3">
                                                                <label htmlFor="val_downgrade_notches" className="block text-sm font-medium mb-1">
                                                                    Downgrade Notches (0-5)
                                                                </label>
                                                                <input
                                                                    id="val_downgrade_notches"
                                                                    type="number"
                                                                    min="0"
                                                                    max="5"
                                                                    className={`input-field ${!canManageTaxonomyFlag ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                                                    value={valueFormData.downgrade_notches ?? ''}
                                                                    onChange={(e) => setValueFormData({
                                                                        ...valueFormData,
                                                                        downgrade_notches: e.target.value === '' ? null : Math.min(5, Math.max(0, parseInt(e.target.value)))
                                                                    })}
                                                                    disabled={!canManageTaxonomyFlag}
                                                                    placeholder="0"
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
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
                                                            onChange={(e) => {
                                                                if (!disableActiveToggle) {
                                                                    setValueFormData({ ...valueFormData, is_active: e.target.checked });
                                                                }
                                                            }}
                                                            disabled={disableActiveToggle}
                                                        />
                                                        <span className="text-sm font-medium">Active</span>
                                                    </label>
                                                    {disableActiveToggle && (
                                                        <p className="text-xs text-gray-500 mt-1">
                                                            System-protected values cannot be deactivated.
                                                        </p>
                                                    )}
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
                                                            {selectedTaxonomy.taxonomy_type === 'bucket' && (
                                                                <>
                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-36">
                                                                        Range (Days)
                                                                    </th>
                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                                                                        Downgrade
                                                                    </th>
                                                                </>
                                                            )}
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
                                                                    {selectedTaxonomy.taxonomy_type === 'bucket' && (
                                                                        <>
                                                                            <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                                                                                {value.min_days === null && value.max_days === null
                                                                                    ? 'All'
                                                                                    : value.min_days === null
                                                                                        ? `≤ ${value.max_days}`
                                                                                        : value.max_days === null
                                                                                            ? `≥ ${value.min_days}`
                                                                                            : `${value.min_days} – ${value.max_days}`
                                                                                }
                                                                            </td>
                                                                            <td className="px-4 py-3 text-sm text-center">
                                                                                {value.downgrade_notches !== null && value.downgrade_notches > 0 ? (
                                                                                    <span className="px-2 py-1 rounded text-xs font-medium bg-amber-100 text-amber-800">
                                                                                        -{value.downgrade_notches}
                                                                                    </span>
                                                                                ) : (
                                                                                    <span className="text-gray-400">0</span>
                                                                                )}
                                                                            </td>
                                                                        </>
                                                                    )}
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
                                                                            {isDeleteProtectedValue(value) ? (
                                                                                <button
                                                                                    disabled
                                                                                    className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-400 rounded text-sm font-medium cursor-not-allowed"
                                                                                    title="This value is system-protected and cannot be deleted"
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

            {/* METHODOLOGY LIBRARY TAB */}
            {activeTab === 'methodology-library' && (
                <>
                    <div className="mb-4 flex justify-between items-start">
                        <p className="text-gray-600 text-sm">
                            Reference library of modeling methodologies organized by category.
                            Click a category to expand/collapse its methodologies.
                        </p>
                        {canManageTaxonomyFlag && (
                            <button onClick={() => setShowMethodologyCategoryForm(true)} className="btn-primary">
                                + New Category
                            </button>
                        )}
                    </div>

                    {/* Category Form */}
                    {showMethodologyCategoryForm && canManageTaxonomyFlag && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">
                                {editingMethodologyCategory ? 'Edit Category' : 'Create New Category'}
                            </h3>
                            <form onSubmit={handleMethodologyCategorySubmit}>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="meth_cat_code" className="block text-sm font-medium mb-2">
                                            Code
                                        </label>
                                        <input
                                            id="meth_cat_code"
                                            type="text"
                                            className="input-field"
                                            value={methodologyCategoryFormData.code}
                                            onChange={(e) => setMethodologyCategoryFormData({ ...methodologyCategoryFormData, code: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="meth_cat_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="meth_cat_name"
                                            type="text"
                                            className="input-field"
                                            value={methodologyCategoryFormData.name}
                                            onChange={(e) => setMethodologyCategoryFormData({ ...methodologyCategoryFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="meth_cat_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="meth_cat_sort"
                                            type="number"
                                            className="input-field"
                                            value={methodologyCategoryFormData.sort_order}
                                            onChange={(e) => setMethodologyCategoryFormData({ ...methodologyCategoryFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4 flex items-center">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                id="meth_cat_is_aiml"
                                                type="checkbox"
                                                checked={methodologyCategoryFormData.is_aiml}
                                                onChange={(e) => setMethodologyCategoryFormData({ ...methodologyCategoryFormData, is_aiml: e.target.checked })}
                                                className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                                            />
                                            <span className="text-sm font-medium text-gray-700">AI/ML Category</span>
                                        </label>
                                        <span className="ml-2 text-xs text-gray-500">(Models using methodologies in this category will be classified as AI/ML)</span>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">
                                        {editingMethodologyCategory ? 'Save' : 'Create'}
                                    </button>
                                    <button type="button" onClick={resetMethodologyCategoryForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Methodology Form */}
                    {showMethodologyForm && canManageTaxonomyFlag && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">
                                {editingMethodology ? 'Edit Methodology' : 'Add New Methodology'}
                            </h3>
                            <form onSubmit={handleMethodologySubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="meth_cat_select" className="block text-sm font-medium mb-2">
                                            Category
                                        </label>
                                        <select
                                            id="meth_cat_select"
                                            className="input-field"
                                            value={methodologyFormData.category_id}
                                            onChange={(e) => setMethodologyFormData({ ...methodologyFormData, category_id: parseInt(e.target.value) })}
                                            required
                                        >
                                            <option value={0}>Select a category...</option>
                                            {methodologyCategories.map(cat => (
                                                <option key={cat.category_id} value={cat.category_id}>
                                                    {cat.name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="meth_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="meth_name"
                                            type="text"
                                            className="input-field"
                                            value={methodologyFormData.name}
                                            onChange={(e) => setMethodologyFormData({ ...methodologyFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="mb-4">
                                    <label htmlFor="meth_desc" className="block text-sm font-medium mb-2">
                                        Description
                                    </label>
                                    <textarea
                                        id="meth_desc"
                                        className="input-field"
                                        rows={2}
                                        value={methodologyFormData.description}
                                        onChange={(e) => setMethodologyFormData({ ...methodologyFormData, description: e.target.value })}
                                    />
                                </div>
                                <div className="mb-4">
                                    <label htmlFor="meth_variants" className="block text-sm font-medium mb-2">
                                        Variants
                                    </label>
                                    <textarea
                                        id="meth_variants"
                                        className="input-field"
                                        rows={2}
                                        value={methodologyFormData.variants}
                                        onChange={(e) => setMethodologyFormData({ ...methodologyFormData, variants: e.target.value })}
                                        placeholder="e.g., Linear, Non-linear, Mixed"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="meth_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="meth_sort"
                                            type="number"
                                            className="input-field"
                                            value={methodologyFormData.sort_order}
                                            onChange={(e) => setMethodologyFormData({ ...methodologyFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4 flex items-center pt-6">
                                        <input
                                            id="meth_active"
                                            type="checkbox"
                                            className="h-4 w-4 text-blue-600 rounded border-gray-300"
                                            checked={methodologyFormData.is_active}
                                            onChange={(e) => setMethodologyFormData({ ...methodologyFormData, is_active: e.target.checked })}
                                        />
                                        <label htmlFor="meth_active" className="ml-2 text-sm font-medium">
                                            Active
                                        </label>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">
                                        {editingMethodology ? 'Save' : 'Create'}
                                    </button>
                                    <button type="button" onClick={resetMethodologyForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {loading ? (
                        <div className="text-center py-8 text-gray-500">Loading...</div>
                    ) : methodologyCategories.length === 0 ? (
                        <div className="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">
                            No methodology categories found.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {methodologyCategories
                                .sort((a, b) => a.sort_order - b.sort_order)
                                .map((category) => (
                                    <div key={category.category_id} className="bg-white rounded-lg shadow-md overflow-hidden">
                                        <div
                                            className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50"
                                            onClick={() => toggleMethodologyCategory(category.category_id)}
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className="text-gray-400">
                                                    {expandedMethodologyCategories.has(category.category_id) ? '▼' : '▶'}
                                                </span>
                                                <span className="font-medium">{category.name}</span>
                                                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                                                    {category.code}
                                                </span>
                                                {category.is_aiml && (
                                                    <span className="text-xs text-purple-700 bg-purple-100 px-2 py-0.5 rounded font-medium">
                                                        AI/ML
                                                    </span>
                                                )}
                                                <span className="text-sm text-gray-500">
                                                    ({category.methodologies?.length || 0} methodologies)
                                                </span>
                                            </div>
                                            {canManageTaxonomyFlag && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleEditMethodologyCategory(category);
                                                    }}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    Edit
                                                </button>
                                            )}
                                        </div>

                                        {expandedMethodologyCategories.has(category.category_id) && (
                                            <div className="border-t bg-gray-50">
                                                {canManageTaxonomyFlag && (
                                                    <div className="px-4 py-2 bg-gray-100 border-b">
                                                        <button
                                                            onClick={() => handleAddMethodologyToCategory(category.category_id)}
                                                            className="text-sm text-blue-600 hover:text-blue-800"
                                                        >
                                                            + Add Methodology
                                                        </button>
                                                    </div>
                                                )}
                                                {category.methodologies && category.methodologies.length > 0 ? (
                                                    <table className="w-full">
                                                        <thead className="bg-gray-100">
                                                            <tr>
                                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Variants</th>
                                                                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase w-20">Status</th>
                                                                {canManageTaxonomyFlag && (
                                                                    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase w-28">Actions</th>
                                                                )}
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-gray-200">
                                                            {category.methodologies
                                                                .sort((a, b) => a.sort_order - b.sort_order)
                                                                .map((methodology) => (
                                                                    <tr key={methodology.methodology_id} className={methodology.is_active ? '' : 'bg-gray-100 text-gray-400'}>
                                                                        <td className="px-4 py-3 text-sm font-medium">
                                                                            {methodology.name}
                                                                        </td>
                                                                        <td className="px-4 py-3 text-sm text-gray-600">
                                                                            {methodology.description || '-'}
                                                                        </td>
                                                                        <td className="px-4 py-3 text-sm text-gray-600">
                                                                            {methodology.variants || '-'}
                                                                        </td>
                                                                        <td className="px-4 py-3 text-center">
                                                                            <span className={`px-2 py-1 text-xs rounded-full ${methodology.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'}`}>
                                                                                {methodology.is_active ? 'Active' : 'Inactive'}
                                                                            </span>
                                                                        </td>
                                                                        {canManageTaxonomyFlag && (
                                                                            <td className="px-4 py-3 text-center">
                                                                                <div className="flex justify-center gap-2">
                                                                                    <button
                                                                                        onClick={() => handleEditMethodology(methodology, category.category_id)}
                                                                                        className="text-blue-600 hover:text-blue-800 text-sm"
                                                                                    >
                                                                                        Edit
                                                                                    </button>
                                                                                    <button
                                                                                        onClick={() => handleToggleMethodologyActive(methodology)}
                                                                                        className={`text-sm ${methodology.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'}`}
                                                                                    >
                                                                                        {methodology.is_active ? 'Deactivate' : 'Activate'}
                                                                                    </button>
                                                                                </div>
                                                                            </td>
                                                                        )}
                                                                    </tr>
                                                                ))}
                                                        </tbody>
                                                    </table>
                                                ) : (
                                                    <div className="px-4 py-3 text-sm text-gray-500 italic">
                                                        No methodologies in this category.
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                        </div>
                    )}
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

            {/* RISK FACTORS TAB */}
            {activeTab === 'risk-factors' && (
                <>
                    {/* Weight Validation Banner */}
                    {weightValidation && !weightValidation.valid && (
                        <div className="mb-4 bg-yellow-50 border-l-4 border-yellow-400 p-4">
                            <div className="flex">
                                <div className="flex-shrink-0">
                                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div className="ml-3">
                                    <p className="text-sm text-yellow-700">
                                        <strong>Weight Validation:</strong> {weightValidation.message || `Total weight is ${(weightValidation.total * 100).toFixed(0)}% (should be 100%)`}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {riskFactorsError && (
                        <div className="mb-4 bg-red-50 border-l-4 border-red-400 p-4">
                            <p className="text-sm text-red-700">{riskFactorsError}</p>
                        </div>
                    )}

                    <div className="mb-6 flex justify-end">
                        <button
                            onClick={() => {
                                resetFactorForm();
                                setShowFactorForm(true);
                            }}
                            className="btn-primary"
                        >
                            + New Factor
                        </button>
                    </div>

                    {/* Factor Form Modal */}
                    {showFactorForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">
                                {editingFactor ? 'Edit Factor' : 'Create New Factor'}
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Code</label>
                                    <input
                                        type="text"
                                        value={factorFormData.code}
                                        onChange={(e) => setFactorFormData({ ...factorFormData, code: e.target.value })}
                                        className="input-field w-full"
                                        placeholder="e.g., COMPLEXITY"
                                    />
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Name</label>
                                    <input
                                        type="text"
                                        value={factorFormData.name}
                                        onChange={(e) => setFactorFormData({ ...factorFormData, name: e.target.value })}
                                        className="input-field w-full"
                                        placeholder="e.g., Model Complexity"
                                    />
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Weight (0.0 - 1.0)</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        max="1"
                                        value={factorFormData.weight}
                                        onChange={(e) => setFactorFormData({ ...factorFormData, weight: parseFloat(e.target.value) || 0 })}
                                        className="input-field w-full"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">All active factor weights must sum to 1.0</p>
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Sort Order</label>
                                    <input
                                        type="number"
                                        value={factorFormData.sort_order}
                                        onChange={(e) => setFactorFormData({ ...factorFormData, sort_order: parseInt(e.target.value) || 0 })}
                                        className="input-field w-full"
                                    />
                                </div>
                                <div className="mb-4 col-span-2">
                                    <label className="block text-sm font-medium mb-2">Description</label>
                                    <textarea
                                        value={factorFormData.description}
                                        onChange={(e) => setFactorFormData({ ...factorFormData, description: e.target.value })}
                                        className="input-field w-full"
                                        rows={2}
                                        placeholder="Description of the factor..."
                                    />
                                </div>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={editingFactor ? handleUpdateFactor : handleCreateFactor}
                                    className="btn-primary"
                                >
                                    {editingFactor ? 'Update' : 'Create'}
                                </button>
                                <button onClick={resetFactorForm} className="btn-secondary">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Factors Master-Detail Layout */}
                    <div className="grid grid-cols-3 gap-6">
                        {/* Factors List */}
                        <div className="col-span-1 bg-white rounded-lg shadow-md p-4">
                            <h3 className="text-lg font-bold mb-4">Factors</h3>
                            {riskFactorsLoading ? (
                                <p className="text-gray-500">Loading...</p>
                            ) : riskFactors.length === 0 ? (
                                <p className="text-gray-500">No factors defined</p>
                            ) : (
                                <ul className="space-y-2">
                                    {riskFactors.map((factor) => (
                                        <li
                                            key={factor.factor_id}
                                            onClick={() => setSelectedFactor(factor)}
                                            className={`p-3 rounded-lg cursor-pointer border ${
                                                selectedFactor?.factor_id === factor.factor_id
                                                    ? 'border-blue-500 bg-blue-50'
                                                    : 'border-gray-200 hover:bg-gray-50'
                                            } ${!factor.is_active ? 'opacity-50' : ''}`}
                                        >
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <p className="font-medium">{factor.name}</p>
                                                    <p className="text-sm text-gray-500">{factor.code}</p>
                                                </div>
                                                <span className={`text-xs px-2 py-1 rounded ${
                                                    factor.is_active
                                                        ? 'bg-green-100 text-green-800'
                                                        : 'bg-gray-100 text-gray-600'
                                                }`}>
                                                    {(factor.weight * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {/* Factor Details */}
                        <div className="col-span-2 bg-white rounded-lg shadow-md p-4">
                            {selectedFactor ? (
                                <>
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-lg font-bold">{selectedFactor.name}</h3>
                                            <p className="text-sm text-gray-500">{selectedFactor.code}</p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => startEditFactor(selectedFactor)}
                                                className="btn-secondary text-sm"
                                            >
                                                Edit
                                            </button>
                                            {selectedFactor.is_active && (
                                                <button
                                                    onClick={() => handleDeleteFactor(selectedFactor.factor_id)}
                                                    className="text-sm px-3 py-1 text-red-600 hover:bg-red-50 rounded"
                                                >
                                                    Deactivate
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                                        <div>
                                            <p className="text-xs text-gray-500 uppercase">Weight</p>
                                            <p className="font-bold text-lg">{(selectedFactor.weight * 100).toFixed(0)}%</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-gray-500 uppercase">Status</p>
                                            <span className={`inline-flex px-2 py-1 text-xs rounded ${
                                                selectedFactor.is_active
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-gray-100 text-gray-600'
                                            }`}>
                                                {selectedFactor.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                        <div>
                                            <p className="text-xs text-gray-500 uppercase">Sort Order</p>
                                            <p className="font-medium">{selectedFactor.sort_order}</p>
                                        </div>
                                    </div>

                                    {selectedFactor.description && (
                                        <div className="mb-6">
                                            <p className="text-xs text-gray-500 uppercase mb-1">Description</p>
                                            <p className="text-gray-700">{selectedFactor.description}</p>
                                        </div>
                                    )}

                                    {/* Guidance Section */}
                                    <div className="border-t pt-4">
                                        <div className="flex justify-between items-center mb-4">
                                            <h4 className="font-bold">Rating Guidance</h4>
                                            <button
                                                onClick={() => {
                                                    resetGuidanceForm();
                                                    setShowGuidanceForm(true);
                                                }}
                                                className="text-sm text-blue-600 hover:text-blue-800"
                                            >
                                                + Add Guidance
                                            </button>
                                        </div>

                                        {/* Guidance Form */}
                                        {showGuidanceForm && (
                                            <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div>
                                                        <label className="block text-sm font-medium mb-1">Rating</label>
                                                        <select
                                                            value={guidanceFormData.rating}
                                                            onChange={(e) => setGuidanceFormData({
                                                                ...guidanceFormData,
                                                                rating: e.target.value as 'HIGH' | 'MEDIUM' | 'LOW',
                                                                points: e.target.value === 'HIGH' ? 3 : e.target.value === 'MEDIUM' ? 2 : 1
                                                            })}
                                                            className="input-field w-full"
                                                        >
                                                            <option value="HIGH">HIGH</option>
                                                            <option value="MEDIUM">MEDIUM</option>
                                                            <option value="LOW">LOW</option>
                                                        </select>
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium mb-1">Points</label>
                                                        <input
                                                            type="number"
                                                            value={guidanceFormData.points}
                                                            onChange={(e) => setGuidanceFormData({ ...guidanceFormData, points: parseInt(e.target.value) || 0 })}
                                                            className="input-field w-full"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium mb-1">Sort Order</label>
                                                        <input
                                                            type="number"
                                                            value={guidanceFormData.sort_order}
                                                            onChange={(e) => setGuidanceFormData({ ...guidanceFormData, sort_order: parseInt(e.target.value) || 0 })}
                                                            className="input-field w-full"
                                                        />
                                                    </div>
                                                    <div className="col-span-3">
                                                        <label className="block text-sm font-medium mb-1">Description</label>
                                                        <textarea
                                                            value={guidanceFormData.description}
                                                            onChange={(e) => setGuidanceFormData({ ...guidanceFormData, description: e.target.value })}
                                                            className="input-field w-full"
                                                            rows={2}
                                                            placeholder="Guidance description..."
                                                        />
                                                    </div>
                                                </div>
                                                <div className="flex gap-2 mt-3">
                                                    <button
                                                        onClick={editingGuidance ? handleUpdateGuidance : handleCreateGuidance}
                                                        className="btn-primary text-sm"
                                                    >
                                                        {editingGuidance ? 'Update' : 'Add'}
                                                    </button>
                                                    <button onClick={resetGuidanceForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        {/* Guidance List */}
                                        {selectedFactor.guidance.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No guidance defined for this factor</p>
                                        ) : (
                                            <div className="space-y-2">
                                                {selectedFactor.guidance.map((g) => (
                                                    <div key={g.guidance_id} className="flex items-start justify-between p-3 border rounded-lg">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2">
                                                                <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                                                    g.rating === 'HIGH' ? 'bg-red-100 text-red-800' :
                                                                    g.rating === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                                    'bg-green-100 text-green-800'
                                                                }`}>
                                                                    {g.rating}
                                                                </span>
                                                                <span className="text-sm text-gray-500">({g.points} pts)</span>
                                                            </div>
                                                            <p className="text-sm text-gray-700 mt-1">{g.description}</p>
                                                        </div>
                                                        <div className="flex gap-1 ml-2">
                                                            <button
                                                                onClick={() => startEditGuidance(g)}
                                                                className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1"
                                                            >
                                                                Edit
                                                            </button>
                                                            <button
                                                                onClick={() => handleDeleteGuidance(g.guidance_id)}
                                                                className="text-xs text-red-600 hover:text-red-800 px-2 py-1"
                                                            >
                                                                Delete
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <p className="text-gray-500">Select a factor to view details</p>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* SCORECARD CONFIG TAB */}
            {activeTab === 'scorecard' && (
                <>
                    {scorecardError && (
                        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                            {scorecardError}
                            <button
                                onClick={() => setScorecardError(null)}
                                className="float-right text-red-700 hover:text-red-900"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {/* Active Version Info */}
                    {scorecardActiveVersion && (
                        <div className={`mb-4 p-4 rounded-lg border ${
                            scorecardActiveVersion.has_unpublished_changes
                                ? 'bg-yellow-50 border-yellow-200'
                                : 'bg-blue-50 border-blue-200'
                        }`}>
                            <div className="flex items-start gap-2">
                                <span className={`text-lg ${
                                    scorecardActiveVersion.has_unpublished_changes ? 'text-yellow-600' : 'text-blue-600'
                                }`}>
                                    {scorecardActiveVersion.has_unpublished_changes ? '⚠️' : 'ℹ️'}
                                </span>
                                <div className={`text-sm flex-1 ${
                                    scorecardActiveVersion.has_unpublished_changes ? 'text-yellow-900' : 'text-blue-900'
                                }`}>
                                    <div className="font-semibold flex items-center gap-2">
                                        Active Version: {scorecardActiveVersion.version_name || `Version ${scorecardActiveVersion.version_number}`}
                                        {scorecardActiveVersion.has_unpublished_changes && (
                                            <span className="bg-yellow-200 text-yellow-800 text-xs px-2 py-0.5 rounded">
                                                Unpublished Changes
                                            </span>
                                        )}
                                    </div>
                                    {scorecardActiveVersion.description && (
                                        <div className="mt-1">{scorecardActiveVersion.description}</div>
                                    )}
                                    <div className={`mt-1 text-xs ${
                                        scorecardActiveVersion.has_unpublished_changes ? 'text-yellow-700' : 'text-blue-700'
                                    }`}>
                                        Published: {scorecardActiveVersion.published_at.split('T')[0]}
                                        {scorecardActiveVersion.published_by_name && ` by ${scorecardActiveVersion.published_by_name}`} |
                                        {' '}{scorecardActiveVersion.sections_count} sections, {scorecardActiveVersion.criteria_count} criteria |
                                        {' '}{scorecardActiveVersion.scorecards_count} scorecard{scorecardActiveVersion.scorecards_count !== 1 ? 's' : ''} linked
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="mb-4 flex justify-between items-center">
                        <h2 className="text-lg font-semibold text-gray-700">
                            Scorecard Configuration
                        </h2>
                        <div className="flex gap-2">
                            {/* Show publish button only if no version exists or there are unpublished changes */}
                            {(!scorecardActiveVersion || scorecardActiveVersion.has_unpublished_changes) && (
                                <button
                                    onClick={() => setShowScorecardPublishModal(true)}
                                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                                >
                                    Publish New Version
                                </button>
                            )}
                            <button
                                onClick={() => {
                                    resetScorecardSectionForm();
                                    setShowScorecardSectionForm(true);
                                }}
                                className="btn-primary"
                            >
                                + New Section
                            </button>
                        </div>
                    </div>

                    {/* Publish Version Modal */}
                    {showScorecardPublishModal && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
                                <div className="p-6">
                                    <h3 className="text-xl font-bold mb-4">Publish New Scorecard Config Version</h3>
                                    <p className="text-gray-600 mb-4">
                                        Publishing a new version will snapshot the current scorecard configuration (sections, criteria, and weights).
                                        New scorecards will use this version. Existing scorecards remain linked to their original version.
                                    </p>
                                    <form onSubmit={handlePublishScorecardVersion}>
                                        <div className="mb-4">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Version Name
                                            </label>
                                            <input
                                                type="text"
                                                value={scorecardPublishForm.version_name}
                                                onChange={(e) => setScorecardPublishForm({ ...scorecardPublishForm, version_name: e.target.value })}
                                                className="input-field"
                                                placeholder="e.g., Q4 2025 Updates"
                                            />
                                        </div>
                                        <div className="mb-6">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Description
                                            </label>
                                            <textarea
                                                value={scorecardPublishForm.description}
                                                onChange={(e) => setScorecardPublishForm({ ...scorecardPublishForm, description: e.target.value })}
                                                className="input-field"
                                                rows={3}
                                                placeholder="Changelog or notes for this version..."
                                            />
                                        </div>
                                        <div className="flex justify-end gap-2">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setShowScorecardPublishModal(false);
                                                    setScorecardPublishForm({ version_name: '', description: '' });
                                                }}
                                                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                                disabled={scorecardPublishing}
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="submit"
                                                disabled={scorecardPublishing}
                                                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                            >
                                                {scorecardPublishing ? 'Publishing...' : 'Publish Version'}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Section Form Modal */}
                    {showScorecardSectionForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6 border border-gray-200">
                            <h3 className="text-lg font-bold mb-4">
                                {editingScorecardSection ? 'Edit Section' : 'Create New Section'}
                            </h3>
                            <form onSubmit={handleScorecardSectionSubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Code</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={scorecardSectionFormData.code}
                                            onChange={(e) => setScorecardSectionFormData({
                                                ...scorecardSectionFormData,
                                                code: e.target.value
                                            })}
                                            required
                                            disabled={!!editingScorecardSection}
                                            placeholder="e.g., 1, 2, 3"
                                        />
                                        {editingScorecardSection && (
                                            <p className="text-xs text-gray-500 mt-1">Code cannot be changed after creation</p>
                                        )}
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Name</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={scorecardSectionFormData.name}
                                            onChange={(e) => setScorecardSectionFormData({
                                                ...scorecardSectionFormData,
                                                name: e.target.value
                                            })}
                                            required
                                            placeholder="e.g., Evaluation of Conceptual Soundness"
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Description</label>
                                        <textarea
                                            className="input-field"
                                            value={scorecardSectionFormData.description}
                                            onChange={(e) => setScorecardSectionFormData({
                                                ...scorecardSectionFormData,
                                                description: e.target.value
                                            })}
                                            rows={2}
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Sort Order</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={scorecardSectionFormData.sort_order}
                                            onChange={(e) => setScorecardSectionFormData({
                                                ...scorecardSectionFormData,
                                                sort_order: parseInt(e.target.value) || 0
                                            })}
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={scorecardSectionFormData.is_active}
                                                onChange={(e) => setScorecardSectionFormData({
                                                    ...scorecardSectionFormData,
                                                    is_active: e.target.checked
                                                })}
                                            />
                                            <span className="text-sm font-medium">Active</span>
                                        </label>
                                    </div>
                                </div>
                                <div className="flex gap-2 mt-4">
                                    <button type="submit" className="btn-primary">
                                        {editingScorecardSection ? 'Update Section' : 'Create Section'}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowScorecardSectionForm(false);
                                            resetScorecardSectionForm();
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Criterion Form Modal */}
                    {showScorecardCriterionForm && selectedScorecardSection && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6 border border-gray-200">
                            <h3 className="text-lg font-bold mb-4">
                                {editingScorecardCriterion ? 'Edit Criterion' : 'Add Criterion to'} Section {selectedScorecardSection.code}
                            </h3>
                            <form onSubmit={handleScorecardCriterionSubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Code</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={scorecardCriterionFormData.code}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                code: e.target.value
                                            })}
                                            required
                                            disabled={!!editingScorecardCriterion}
                                            placeholder={`e.g., ${selectedScorecardSection.code}.1`}
                                        />
                                        {editingScorecardCriterion && (
                                            <p className="text-xs text-gray-500 mt-1">Code cannot be changed after creation</p>
                                        )}
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Name</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={scorecardCriterionFormData.name}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                name: e.target.value
                                            })}
                                            required
                                            placeholder="e.g., Model Development Documentation"
                                        />
                                    </div>
                                    <div className="mb-4 col-span-2">
                                        <label className="block text-sm font-medium mb-2">Description Prompt</label>
                                        <textarea
                                            className="input-field"
                                            value={scorecardCriterionFormData.description_prompt}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                description_prompt: e.target.value
                                            })}
                                            rows={2}
                                            placeholder="Prompt guiding validator's description entry"
                                        />
                                    </div>
                                    <div className="mb-4 col-span-2">
                                        <label className="block text-sm font-medium mb-2">Comments Prompt</label>
                                        <textarea
                                            className="input-field"
                                            value={scorecardCriterionFormData.comments_prompt}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                comments_prompt: e.target.value
                                            })}
                                            rows={2}
                                            placeholder="Prompt guiding validator's comments entry"
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Weight</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            min="0"
                                            className="input-field"
                                            value={scorecardCriterionFormData.weight}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                weight: parseFloat(e.target.value) || 1.0
                                            })}
                                        />
                                        <p className="text-xs text-gray-500 mt-1">Weight for scoring calculation (default: 1.0)</p>
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Sort Order</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={scorecardCriterionFormData.sort_order}
                                            onChange={(e) => setScorecardCriterionFormData({
                                                ...scorecardCriterionFormData,
                                                sort_order: parseInt(e.target.value) || 0
                                            })}
                                        />
                                    </div>
                                    <div className="mb-4 flex gap-6">
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={scorecardCriterionFormData.allow_zero}
                                                onChange={(e) => setScorecardCriterionFormData({
                                                    ...scorecardCriterionFormData,
                                                    allow_zero: e.target.checked
                                                })}
                                            />
                                            <span className="text-sm font-medium">Allow N/A</span>
                                        </label>
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={scorecardCriterionFormData.is_active}
                                                onChange={(e) => setScorecardCriterionFormData({
                                                    ...scorecardCriterionFormData,
                                                    is_active: e.target.checked
                                                })}
                                            />
                                            <span className="text-sm font-medium">Active</span>
                                        </label>
                                    </div>
                                </div>
                                <div className="flex gap-2 mt-4">
                                    <button type="submit" className="btn-primary">
                                        {editingScorecardCriterion ? 'Update Criterion' : 'Add Criterion'}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowScorecardCriterionForm(false);
                                            resetScorecardCriterionForm();
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Master-Detail Layout */}
                    {scorecardLoading ? (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-2 text-gray-500">Loading scorecard configuration...</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-12 gap-6">
                            {/* Sections List (Left) */}
                            <div className="col-span-4">
                                <div className="bg-white rounded-lg shadow-md">
                                    <div className="p-4 border-b border-gray-200">
                                        <h3 className="font-semibold text-gray-700">Sections</h3>
                                    </div>
                                    <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                                        {scorecardSections.length === 0 ? (
                                            <p className="p-4 text-gray-500 text-sm">No sections configured</p>
                                        ) : (
                                            scorecardSections.map((section) => (
                                                <div
                                                    key={section.section_id}
                                                    className={`p-4 cursor-pointer hover:bg-gray-50 ${
                                                        selectedScorecardSection?.section_id === section.section_id
                                                            ? 'bg-blue-50 border-l-4 border-blue-500'
                                                            : ''
                                                    }`}
                                                    onClick={() => setSelectedScorecardSection(section)}
                                                >
                                                    <div className="flex justify-between items-start">
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">
                                                                    {section.code}
                                                                </span>
                                                                <span className="font-medium text-gray-900">
                                                                    {section.name}
                                                                </span>
                                                            </div>
                                                            {!section.is_active && (
                                                                <span className="text-xs text-red-600 mt-1">Inactive</span>
                                                            )}
                                                            <p className="text-xs text-gray-500 mt-1">
                                                                {section.criteria?.length || 0} criteria
                                                            </p>
                                                        </div>
                                                        <div className="flex gap-1">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    startEditScorecardSection(section);
                                                                }}
                                                                className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1"
                                                            >
                                                                Edit
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleDeleteScorecardSection(section.section_id);
                                                                }}
                                                                className="text-xs text-red-600 hover:text-red-800 px-2 py-1"
                                                            >
                                                                Delete
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Criteria Detail (Right) */}
                            <div className="col-span-8">
                                <div className="bg-white rounded-lg shadow-md">
                                    <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                                        <h3 className="font-semibold text-gray-700">
                                            {selectedScorecardSection
                                                ? `Criteria - Section ${selectedScorecardSection.code}: ${selectedScorecardSection.name}`
                                                : 'Criteria'}
                                        </h3>
                                        {selectedScorecardSection && (
                                            <button
                                                onClick={() => {
                                                    resetScorecardCriterionForm();
                                                    setShowScorecardCriterionForm(true);
                                                }}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Criterion
                                            </button>
                                        )}
                                    </div>
                                    <div className="p-4">
                                        {selectedScorecardSection ? (
                                            selectedScorecardSection.criteria?.length === 0 ? (
                                                <p className="text-gray-500 text-sm">No criteria in this section</p>
                                            ) : (
                                                <div className="space-y-3">
                                                    {selectedScorecardSection.criteria
                                                        ?.sort((a, b) => a.sort_order - b.sort_order)
                                                        .map((criterion) => (
                                                            <div
                                                                key={criterion.criterion_id}
                                                                className={`p-4 border rounded-lg ${
                                                                    criterion.is_active
                                                                        ? 'border-gray-200'
                                                                        : 'border-red-200 bg-red-50'
                                                                }`}
                                                            >
                                                                <div className="flex justify-between items-start">
                                                                    <div className="flex-1">
                                                                        <div className="flex items-center gap-2 mb-2">
                                                                            <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">
                                                                                {criterion.code}
                                                                            </span>
                                                                            <span className="font-medium text-gray-900">
                                                                                {criterion.name}
                                                                            </span>
                                                                            {!criterion.is_active && (
                                                                                <span className="text-xs text-red-600 px-2 py-0.5 bg-red-100 rounded">
                                                                                    Inactive
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                                                                            <div>
                                                                                <span className="font-medium">Weight:</span>{' '}
                                                                                <span className={criterion.weight !== 1.0 ? 'text-blue-600 font-medium' : ''}>
                                                                                    {criterion.weight}
                                                                                </span>
                                                                            </div>
                                                                            <div>
                                                                                <span className="font-medium">Allow N/A:</span>{' '}
                                                                                {criterion.allow_zero ? 'Yes' : 'No'}
                                                                            </div>
                                                                        </div>
                                                                        {criterion.description_prompt && (
                                                                            <p className="text-xs text-gray-500 mt-2 truncate">
                                                                                <span className="font-medium">Description:</span> {criterion.description_prompt}
                                                                            </p>
                                                                        )}
                                                                    </div>
                                                                    <div className="flex gap-1 ml-4">
                                                                        <button
                                                                            onClick={() => startEditScorecardCriterion(criterion)}
                                                                            className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1"
                                                                        >
                                                                            Edit
                                                                        </button>
                                                                        <button
                                                                            onClick={() => handleDeleteScorecardCriterion(criterion.criterion_id)}
                                                                            className="text-xs text-red-600 hover:text-red-800 px-2 py-1"
                                                                        >
                                                                            Delete
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))}
                                                </div>
                                            )
                                        ) : (
                                            <p className="text-gray-500">Select a section to view criteria</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* RESIDUAL RISK MAP TAB */}
            {activeTab === 'residual-risk-map' && (
                <>
                    {residualRiskMapError && (
                        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                            {residualRiskMapError}
                            <button
                                onClick={() => setResidualRiskMapError(null)}
                                className="float-right text-red-700 hover:text-red-900"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {residualRiskMapLoading ? (
                        <div className="text-center py-12">Loading...</div>
                    ) : (
                        <>
                            {/* Active Version Info */}
                            {residualRiskMapConfig && (
                                <div className="mb-4 p-4 rounded-lg border bg-blue-50 border-blue-200">
                                    <div className="flex items-start gap-2">
                                        <span className="text-lg text-blue-600">ℹ️</span>
                                        <div className="text-sm flex-1 text-blue-900">
                                            <div className="font-semibold">
                                                Active Version: {residualRiskMapConfig.version_name || `Version ${residualRiskMapConfig.version_number}`}
                                            </div>
                                            {residualRiskMapConfig.description && (
                                                <div className="mt-1">{residualRiskMapConfig.description}</div>
                                            )}
                                            <div className="mt-1 text-xs text-blue-700">
                                                Created: {residualRiskMapConfig.created_at.split('T')[0]}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="mb-4 flex justify-between items-center">
                                <div>
                                    <h2 className="text-lg font-semibold text-gray-700">
                                        Residual Risk Map Configuration
                                    </h2>
                                    <p className="text-sm text-gray-500">
                                        Defines how Inherent Risk Tier and Scorecard Outcome combine to determine Residual Risk
                                    </p>
                                </div>
                                {!showResidualRiskMapEditor && (
                                    <button
                                        onClick={startEditResidualRiskMap}
                                        className="btn-primary"
                                    >
                                        Edit Matrix
                                    </button>
                                )}
                            </div>

                            {/* Matrix Display / Editor */}
                            {showResidualRiskMapEditor ? (
                                <form onSubmit={handleSaveResidualRiskMap}>
                                    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                                        <h3 className="text-md font-semibold mb-4">Edit Risk Matrix</h3>

                                        {/* Version Info Form */}
                                        <div className="grid grid-cols-2 gap-4 mb-6">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Version Name (optional)
                                                </label>
                                                <input
                                                    type="text"
                                                    value={residualRiskMapPublishForm.version_name}
                                                    onChange={(e) => setResidualRiskMapPublishForm(prev => ({ ...prev, version_name: e.target.value }))}
                                                    className="input-field"
                                                    placeholder="e.g., Q4 2025 Update"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Description (optional)
                                                </label>
                                                <input
                                                    type="text"
                                                    value={residualRiskMapPublishForm.description}
                                                    onChange={(e) => setResidualRiskMapPublishForm(prev => ({ ...prev, description: e.target.value }))}
                                                    className="input-field"
                                                    placeholder="Changelog or notes..."
                                                />
                                            </div>
                                        </div>

                                        {/* Matrix Editor Table */}
                                        <div className="overflow-x-auto">
                                            <table className="min-w-full border-collapse">
                                                <thead>
                                                    <tr>
                                                        <th className="border border-gray-300 bg-gray-100 p-2 text-sm font-medium text-gray-700">
                                                            Inherent Risk ↓ / Scorecard →
                                                        </th>
                                                        {DEFAULT_COLUMN_VALUES.map(col => (
                                                            <th key={col} className="border border-gray-300 bg-gray-100 p-2 text-sm font-medium text-gray-700 text-center">
                                                                {col}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {DEFAULT_ROW_VALUES.map(row => (
                                                        <tr key={row}>
                                                            <td className="border border-gray-300 bg-gray-50 p-2 text-sm font-medium text-gray-700">
                                                                {row}
                                                            </td>
                                                            {DEFAULT_COLUMN_VALUES.map(col => (
                                                                <td key={`${row}-${col}`} className="border border-gray-300 p-1">
                                                                    <select
                                                                        value={residualRiskMapEditMatrix[row]?.[col] || 'Medium'}
                                                                        onChange={(e) => handleResidualRiskMapCellChange(row, col, e.target.value)}
                                                                        className={`w-full p-2 text-sm rounded border-0 ${getResidualRiskColorClass(residualRiskMapEditMatrix[row]?.[col])}`}
                                                                    >
                                                                        {DEFAULT_RESULT_VALUES.map(val => (
                                                                            <option key={val} value={val}>{val}</option>
                                                                        ))}
                                                                    </select>
                                                                </td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>

                                        <div className="flex justify-end gap-2 mt-6">
                                            <button
                                                type="button"
                                                onClick={cancelEditResidualRiskMap}
                                                className="btn-secondary"
                                                disabled={residualRiskMapSaving}
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="submit"
                                                className="btn-primary"
                                                disabled={residualRiskMapSaving}
                                            >
                                                {residualRiskMapSaving ? 'Saving...' : 'Save New Version'}
                                            </button>
                                        </div>
                                    </div>
                                </form>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    {/* Read-only Matrix Display */}
                                    {residualRiskMapConfig ? (
                                        <div className="overflow-x-auto">
                                            <table className="min-w-full border-collapse">
                                                <thead>
                                                    <tr>
                                                        <th className="border border-gray-300 bg-gray-100 p-3 text-sm font-medium text-gray-700">
                                                            {residualRiskMapConfig.matrix_config.row_axis_label} ↓ / {residualRiskMapConfig.matrix_config.column_axis_label} →
                                                        </th>
                                                        {DEFAULT_COLUMN_VALUES.map(col => (
                                                            <th key={col} className="border border-gray-300 bg-gray-100 p-3 text-sm font-medium text-gray-700 text-center">
                                                                {col}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {DEFAULT_ROW_VALUES.map(row => (
                                                        <tr key={row}>
                                                            <td className="border border-gray-300 bg-gray-50 p-3 text-sm font-medium text-gray-700">
                                                                {row}
                                                            </td>
                                                            {DEFAULT_COLUMN_VALUES.map(col => {
                                                                const cellValue = residualRiskMapConfig.matrix_config.matrix[row]?.[col] || 'N/A';
                                                                return (
                                                                    <td
                                                                        key={`${row}-${col}`}
                                                                        className={`border border-gray-300 p-3 text-sm font-medium text-center ${getResidualRiskColorClass(cellValue)}`}
                                                                    >
                                                                        {cellValue}
                                                                    </td>
                                                                );
                                                            })}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <div className="text-center py-8 text-gray-500">
                                            <p>No residual risk map configuration found.</p>
                                            <p className="mt-2">Click "Edit Matrix" to create one.</p>
                                        </div>
                                    )}

                                    {/* Version History */}
                                    {residualRiskMapVersions.length > 1 && (
                                        <div className="mt-6 border-t pt-4">
                                            <h4 className="text-sm font-semibold text-gray-700 mb-3">Version History</h4>
                                            <div className="space-y-2">
                                                {residualRiskMapVersions.map(version => (
                                                    <div
                                                        key={version.config_id}
                                                        className={`flex items-center justify-between p-2 rounded text-sm ${
                                                            version.is_active ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'
                                                        }`}
                                                    >
                                                        <div>
                                                            <span className="font-medium">
                                                                {version.version_name || `Version ${version.version_number}`}
                                                            </span>
                                                            {version.is_active && (
                                                                <span className="ml-2 text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded">
                                                                    Active
                                                                </span>
                                                            )}
                                                            {version.description && (
                                                                <span className="ml-2 text-gray-500">- {version.description}</span>
                                                            )}
                                                        </div>
                                                        <div className="text-gray-500 text-xs">
                                                            {version.created_at.split('T')[0]}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </>
            )}

            {/* ORGANIZATIONS (LOB) TAB */}
            {activeTab === 'organizations' && (
                <>
                    <div className="mb-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-2">
                            Organization Hierarchy (Lines of Business)
                        </h2>
                        <p className="text-gray-600 text-sm">
                            Manage the organizational hierarchy structure. Users are assigned to LOB units for reporting and access control.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* LOB Tree - 2 columns */}
                        <div className="lg:col-span-2">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="text-lg font-semibold mb-4">LOB Hierarchy</h3>
                                <LOBTreeView
                                    showInactive={true}
                                    onSelectLOB={(lob) => setSelectedLOB(lob)}
                                    selectedLOBId={selectedLOB?.lob_id}
                                />
                            </div>
                        </div>

                        {/* Right column - Details Panel or Import Panel */}
                        <div className="lg:col-span-1 space-y-4">
                            {/* LOB Detail Panel */}
                            {selectedLOB && (
                                <div className="bg-white rounded-lg shadow-md p-4">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-lg font-semibold">LOB Details</h3>
                                        <button
                                            onClick={() => setSelectedLOB(null)}
                                            className="text-gray-400 hover:text-gray-600"
                                            title="Close"
                                        >
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                            </svg>
                                        </button>
                                    </div>

                                    {/* Header with org_unit badge */}
                                    <div className="mb-4 pb-4 border-b border-gray-200">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-mono font-bold bg-blue-100 text-blue-800">
                                                {selectedLOB.org_unit}
                                            </span>
                                            {!selectedLOB.is_active && (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                                                    Inactive
                                                </span>
                                            )}
                                        </div>
                                        <h4 className="text-lg font-semibold text-gray-900">{selectedLOB.name}</h4>
                                        <p className="text-sm text-gray-500">Code: {selectedLOB.code}</p>
                                    </div>

                                    {/* Path */}
                                    <div className="mb-4">
                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Full Path</label>
                                        <p className="text-sm text-gray-800 break-words">{selectedLOB.full_path}</p>
                                    </div>

                                    {/* Grid of basic info */}
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Level</label>
                                            <p className="text-sm text-gray-800">{selectedLOB.level}</p>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Sort Order</label>
                                            <p className="text-sm text-gray-800">{selectedLOB.sort_order}</p>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Users</label>
                                            <p className="text-sm text-gray-800">
                                                {selectedLOB.user_count} user{selectedLOB.user_count !== 1 ? 's' : ''}
                                            </p>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Children</label>
                                            <p className="text-sm text-gray-800">
                                                {selectedLOB.children?.length || 0} child node{(selectedLOB.children?.length || 0) !== 1 ? 's' : ''}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Description (if any) */}
                                    {selectedLOB.description && (
                                        <div className="mb-4">
                                            <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Description</label>
                                            <p className="text-sm text-gray-800">{selectedLOB.description}</p>
                                        </div>
                                    )}

                                    {/* Metadata Section (if any metadata fields exist) */}
                                    {(selectedLOB.contact_name || selectedLOB.legal_entity_name || selectedLOB.short_name || selectedLOB.tier || selectedLOB.status_code) && (
                                        <div className="border-t border-gray-200 pt-4 mt-4">
                                            <h5 className="text-sm font-semibold text-gray-700 mb-3">Additional Metadata</h5>
                                            <div className="space-y-3">
                                                {selectedLOB.contact_name && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Contact</label>
                                                        <p className="text-sm text-gray-800">{selectedLOB.contact_name}</p>
                                                    </div>
                                                )}
                                                {selectedLOB.legal_entity_name && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Legal Entity</label>
                                                        <p className="text-sm text-gray-800">
                                                            {selectedLOB.legal_entity_name}
                                                            {selectedLOB.legal_entity_id && (
                                                                <span className="text-gray-500 ml-1">({selectedLOB.legal_entity_id})</span>
                                                            )}
                                                        </p>
                                                    </div>
                                                )}
                                                {selectedLOB.short_name && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Short Name</label>
                                                        <p className="text-sm text-gray-800">{selectedLOB.short_name}</p>
                                                    </div>
                                                )}
                                                {selectedLOB.tier && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Tier</label>
                                                        <p className="text-sm text-gray-800">{selectedLOB.tier}</p>
                                                    </div>
                                                )}
                                                {selectedLOB.status_code && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Status Code</label>
                                                        <p className="text-sm text-gray-800">{selectedLOB.status_code}</p>
                                                    </div>
                                                )}
                                                {selectedLOB.org_description && (
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Org Description</label>
                                                        <p className="text-sm text-gray-800">{selectedLOB.org_description}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Import Panel - Admin only */}
                            {canManageTaxonomyFlag && (
                                <LOBImportPanel
                                    onImportComplete={() => {
                                        // Force re-render of tree by toggling a key
                                        // The LOBTreeView component will re-fetch data
                                        setSelectedLOB(null);
                                    }}
                                />
                            )}

                            {/* Help text for non-admins when nothing is selected */}
                            {!canManageTaxonomyFlag && !selectedLOB && (
                                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                    <h3 className="text-lg font-semibold mb-2">LOB Structure</h3>
                                    <p className="text-sm text-gray-600">
                                        The organization hierarchy shows the Lines of Business (LOB) structure.
                                        Click on any node to view its details.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* COMPONENT DEFINITIONS TAB */}
            {activeTab === 'component-definitions' && (
                <>
                    <div className="space-y-6">
                        {/* Header */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h1 className="text-2xl font-bold text-gray-900">Component Definition Management</h1>
                                    <p className="text-gray-600 mt-2">
                                        Manage validation component expectations for different risk tiers. Changes require publishing a new component definition version.
                                    </p>
                                </div>
                                <button
                                    onClick={() => setShowComponentPublishModal(true)}
                                    className="btn-primary"
                                >
                                    Publish New Version
                                </button>
                            </div>

                            {/* Active Configuration Info */}
                            {activeComponentConfig && (
                                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
                                    <div className="flex items-start gap-2">
                                        <span className="text-blue-600 text-lg">ℹ️</span>
                                        <div className="text-sm text-blue-900">
                                            <div className="font-semibold">Active Configuration: {activeComponentConfig.config_name}</div>
                                            {activeComponentConfig.description && (
                                                <div className="mt-1">{activeComponentConfig.description}</div>
                                            )}
                                            <div className="mt-1 text-xs">
                                                Effective Date: {activeComponentConfig.effective_date.split('T')[0]} |
                                                Created: {activeComponentConfig.created_at.split('T')[0]}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Subtabs */}
                        <div className="border-b border-gray-200">
                            <nav className="-mb-px flex space-x-8">
                                <button
                                    onClick={() => handleComponentTabChange('definitions')}
                                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                        componentTab === 'definitions'
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                                >
                                    Definitions
                                </button>
                                <button
                                    onClick={() => handleComponentTabChange('version-history')}
                                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                        componentTab === 'version-history'
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                                >
                                    Version History
                                </button>
                            </nav>
                        </div>

                        {/* Messages */}
                        {componentDefError && (
                            <div className="bg-red-50 border border-red-200 rounded p-4 text-red-800">
                                {componentDefError}
                            </div>
                        )}

                        {componentDefSuccess && (
                            <div className="bg-green-50 border border-green-200 rounded p-4 text-green-800">
                                {componentDefSuccess}
                            </div>
                        )}

                        {componentTab === 'definitions' && (
                            <>
                                {/* Component Definitions Table */}
                                {componentDefLoading ? (
                                    <div className="flex items-center justify-center p-8">
                                        <div className="text-gray-600">Loading component definitions...</div>
                                    </div>
                                ) : (
                                    sections.map(sectionKey => {
                                        const [sectionNum, sectionTitle] = sectionKey.split('|');
                                        const sectionComponents = groupedComponents[sectionKey];

                                        return (
                                            <div key={sectionKey} className="bg-white rounded-lg shadow-md overflow-hidden">
                                                <div className="bg-gray-100 px-6 py-3 border-b">
                                                    <h2 className="font-semibold text-gray-800">
                                                        Section {sectionNum} – {sectionTitle}
                                                    </h2>
                                                </div>

                                                <div className="overflow-x-auto">
                                                    <table className="min-w-full">
                                                        <thead className="bg-gray-50">
                                                            <tr>
                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/4">
                                                                    Component
                                                                </th>
                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                                    Tier 1 (High)
                                                                </th>
                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                                    Tier 2 (Medium)
                                                                </th>
                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                                    Tier 3 (Low)
                                                                </th>
                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                                    Tier 4 (Very Low)
                                                                </th>
                                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase w-24">
                                                                    Actions
                                                                </th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="bg-white divide-y divide-gray-200">
                                                            {sectionComponents.map(component => {
                                                                const isEditing = editingComponentId === component.component_id;

                                                                return (
                                                                    <tr key={component.component_id}>
                                                                        <td className="px-6 py-4">
                                                                            <div className="text-sm font-medium text-gray-900">
                                                                                {component.component_code}
                                                                            </div>
                                                                            <div className="text-sm text-gray-600">
                                                                                {component.component_title}
                                                                            </div>
                                                                        </td>

                                                                        {/* Expectation columns */}
                                                                        {isEditing ? (
                                                                            <>
                                                                                <td className="px-6 py-4">
                                                                                    <select
                                                                                        value={componentEditForm.expectation_high}
                                                                                        onChange={(e) => setComponentEditForm({ ...componentEditForm, expectation_high: e.target.value })}
                                                                                        className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                                    >
                                                                                        <option value="Required">Required</option>
                                                                                        <option value="IfApplicable">If Applicable</option>
                                                                                        <option value="NotExpected">Not Expected</option>
                                                                                    </select>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <select
                                                                                        value={componentEditForm.expectation_medium}
                                                                                        onChange={(e) => setComponentEditForm({ ...componentEditForm, expectation_medium: e.target.value })}
                                                                                        className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                                    >
                                                                                        <option value="Required">Required</option>
                                                                                        <option value="IfApplicable">If Applicable</option>
                                                                                        <option value="NotExpected">Not Expected</option>
                                                                                    </select>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <select
                                                                                        value={componentEditForm.expectation_low}
                                                                                        onChange={(e) => setComponentEditForm({ ...componentEditForm, expectation_low: e.target.value })}
                                                                                        className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                                    >
                                                                                        <option value="Required">Required</option>
                                                                                        <option value="IfApplicable">If Applicable</option>
                                                                                        <option value="NotExpected">Not Expected</option>
                                                                                    </select>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <select
                                                                                        value={componentEditForm.expectation_very_low}
                                                                                        onChange={(e) => setComponentEditForm({ ...componentEditForm, expectation_very_low: e.target.value })}
                                                                                        className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                                    >
                                                                                        <option value="Required">Required</option>
                                                                                        <option value="IfApplicable">If Applicable</option>
                                                                                        <option value="NotExpected">Not Expected</option>
                                                                                    </select>
                                                                                </td>
                                                                            </>
                                                                        ) : (
                                                                            <>
                                                                                <td className="px-6 py-4">
                                                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_high)}`}>
                                                                                        {formatExpectation(component.expectation_high)}
                                                                                    </span>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_medium)}`}>
                                                                                        {formatExpectation(component.expectation_medium)}
                                                                                    </span>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_low)}`}>
                                                                                        {formatExpectation(component.expectation_low)}
                                                                                    </span>
                                                                                </td>
                                                                                <td className="px-6 py-4">
                                                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_very_low)}`}>
                                                                                        {formatExpectation(component.expectation_very_low)}
                                                                                    </span>
                                                                                </td>
                                                                            </>
                                                                        )}

                                                                        {/* Actions */}
                                                                        <td className="px-6 py-4 text-right text-sm">
                                                                            {isEditing ? (
                                                                                <div className="flex gap-2 justify-end">
                                                                                    <button
                                                                                        onClick={() => handleComponentSaveEdit(component.component_id)}
                                                                                        disabled={componentDefLoading}
                                                                                        className="text-blue-600 hover:text-blue-800"
                                                                                    >
                                                                                        Save
                                                                                    </button>
                                                                                    <button
                                                                                        onClick={handleComponentCancelEdit}
                                                                                        disabled={componentDefLoading}
                                                                                        className="text-gray-600 hover:text-gray-800"
                                                                                    >
                                                                                        Cancel
                                                                                    </button>
                                                                                </div>
                                                                            ) : (
                                                                                <button
                                                                                    onClick={() => handleComponentEditClick(component)}
                                                                                    className="text-blue-600 hover:text-blue-800"
                                                                                >
                                                                                    Edit
                                                                                </button>
                                                                            )}
                                                                        </td>
                                                                    </tr>
                                                                );
                                                            })}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </>
                        )}

                        {componentTab === 'version-history' && (
                            <div className="space-y-4">
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                    <div className="flex items-start">
                                        <div className="flex-shrink-0">
                                            <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                                <path
                                                    fillRule="evenodd"
                                                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                                    clipRule="evenodd"
                                                />
                                            </svg>
                                        </div>
                                        <div className="ml-3">
                                            <h3 className="text-sm font-medium text-blue-800">About Component Definition Versioning</h3>
                                            <div className="mt-2 text-sm text-blue-700">
                                                <p>
                                                    Component definition versions represent point-in-time snapshots of all validation component requirements.
                                                    When a validation plan is locked (moved to Review or Pending Approval), it captures the active
                                                    component definitions at that moment, ensuring historical compliance and preventing retroactive changes.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {componentConfigHistoryError && (
                                    <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
                                        {componentConfigHistoryError}
                                    </div>
                                )}

                                {componentConfigHistoryLoading ? (
                                    <div className="text-center py-12">
                                        <div className="text-gray-500">Loading component definition history...</div>
                                    </div>
                                ) : componentConfigHistory.length === 0 ? (
                                    <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                                        No component definition versions found.
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {componentConfigHistory.map(config => (
                                            <div key={config.config_id} className="bg-white rounded-lg shadow-md overflow-hidden">
                                                <div
                                                    className="px-6 py-4 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
                                                    onClick={() => handleExpandComponentConfiguration(config.config_id)}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center space-x-4">
                                                            <div>
                                                                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                                                    {config.config_name}
                                                                    {config.is_active && (
                                                                        <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                                                                            ACTIVE
                                                                        </span>
                                                                    )}
                                                                </h3>
                                                                <p className="text-sm text-gray-600 mt-1">
                                                                    {config.description || 'No description'}
                                                                </p>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center space-x-6 text-sm text-gray-600">
                                                            <div>
                                                                <span className="font-medium">Effective Date:</span>{' '}
                                                                {config.effective_date.split('T')[0]}
                                                            </div>
                                                            <div>
                                                                <span className="font-medium">Created:</span>{' '}
                                                                {config.created_at.split('T')[0]}
                                                            </div>
                                                            <svg
                                                                className={`w-5 h-5 text-gray-500 transition-transform ${
                                                                    expandedComponentConfigId === config.config_id ? 'rotate-180' : ''
                                                                }`}
                                                                fill="none"
                                                                stroke="currentColor"
                                                                viewBox="0 0 24 24"
                                                            >
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                            </svg>
                                                        </div>
                                                    </div>
                                                </div>

                                                {expandedComponentConfigId === config.config_id && (
                                                    <div className="px-6 py-4">
                                                        {componentConfigDetailLoading ? (
                                                            <div className="text-center py-8 text-gray-500">
                                                                Loading configuration details...
                                                            </div>
                                                        ) : expandedComponentConfig ? (
                                                            <div className="space-y-4">
                                                                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                                                                    <p className="text-sm text-blue-800">
                                                                        <strong>Configuration Snapshot:</strong> This configuration contains{' '}
                                                                        {expandedComponentConfig.config_items?.length || 0} component definitions as they existed on{' '}
                                                                        {config.effective_date.split('T')[0]}.
                                                                    </p>
                                                                </div>

                                                                {expandedComponentConfig.config_items && expandedComponentConfig.config_items.length > 0 ? (
                                                                    <>
                                                                        {Object.entries(groupComponentConfigItemsBySection(expandedComponentConfig.config_items)).map(([sectionKey, items]) => {
                                                                            const [sectionNum, sectionTitle] = sectionKey.split('|');
                                                                            return (
                                                                                <div key={sectionKey} className="border rounded-lg overflow-hidden">
                                                                                    <div className="bg-gray-100 px-4 py-2 border-b">
                                                                                        <h4 className="font-semibold text-gray-800">
                                                                                            Section {sectionNum} – {sectionTitle}
                                                                                        </h4>
                                                                                    </div>
                                                                                    <div className="overflow-x-auto">
                                                                                        <table className="min-w-full divide-y divide-gray-200">
                                                                                            <thead className="bg-gray-50">
                                                                                                <tr>
                                                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                        Component
                                                                                                    </th>
                                                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                        High Risk
                                                                                                    </th>
                                                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                        Medium Risk
                                                                                                    </th>
                                                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                        Low Risk
                                                                                                    </th>
                                                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                        Very Low Risk
                                                                                                    </th>
                                                                                                </tr>
                                                                                            </thead>
                                                                                            <tbody className="bg-white divide-y divide-gray-200">
                                                                                                {items.map(item => (
                                                                                                    <tr key={item.config_item_id} className="hover:bg-gray-50">
                                                                                                        <td className="px-4 py-3">
                                                                                                            <div className="text-sm font-medium text-gray-900">
                                                                                                                {item.component_code}
                                                                                                            </div>
                                                                                                            <div className="text-sm text-gray-500">
                                                                                                                {item.component_title}
                                                                                                            </div>
                                                                                                        </td>
                                                                                                        <td className="px-4 py-3">
                                                                                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadge(item.expectation_high)}`}>
                                                                                                                {formatExpectation(item.expectation_high)}
                                                                                                            </span>
                                                                                                        </td>
                                                                                                        <td className="px-4 py-3">
                                                                                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadge(item.expectation_medium)}`}>
                                                                                                                {formatExpectation(item.expectation_medium)}
                                                                                                            </span>
                                                                                                        </td>
                                                                                                        <td className="px-4 py-3">
                                                                                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadge(item.expectation_low)}`}>
                                                                                                                {formatExpectation(item.expectation_low)}
                                                                                                            </span>
                                                                                                        </td>
                                                                                                        <td className="px-4 py-3">
                                                                                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadge(item.expectation_very_low)}`}>
                                                                                                                {formatExpectation(item.expectation_very_low)}
                                                                                                            </span>
                                                                                                        </td>
                                                                                                    </tr>
                                                                                                ))}
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </div>
                                                                                </div>
                                                                            );
                                                                        })}
                                                                    </>
                                                                ) : (
                                                                    <div className="text-center py-8 text-gray-500">
                                                                        No component items found for this configuration.
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ) : null}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Publish Configuration Modal */}
                        {showComponentPublishModal && (
                            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                                <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
                                    <div className="p-6">
                                        <h2 className="text-2xl font-bold mb-4">Publish New Component Definition Version</h2>
                                        <p className="text-gray-600 mb-6">
                                            Publishing a new version will snapshot the current component definitions.
                                            New validation plans will use this version. Existing locked plans will remain linked to their original version.
                                        </p>

                                        <div className="space-y-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Version Name <span className="text-red-500">*</span>
                                                </label>
                                                <input
                                                    type="text"
                                                    value={componentPublishForm.config_name}
                                                    onChange={(e) => setComponentPublishForm({ ...componentPublishForm, config_name: e.target.value })}
                                                    placeholder="e.g., Q4 2025 Requirements Update"
                                                    className="w-full border border-gray-300 rounded px-3 py-2"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Description
                                                </label>
                                                <textarea
                                                    value={componentPublishForm.description}
                                                    onChange={(e) => setComponentPublishForm({ ...componentPublishForm, description: e.target.value })}
                                                    placeholder="Describe what changed in this version..."
                                                    rows={3}
                                                    className="w-full border border-gray-300 rounded px-3 py-2"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Effective Date
                                                </label>
                                                <input
                                                    type="date"
                                                    value={componentPublishForm.effective_date}
                                                    onChange={(e) => setComponentPublishForm({ ...componentPublishForm, effective_date: e.target.value })}
                                                    className="border border-gray-300 rounded px-3 py-2"
                                                />
                                            </div>
                                        </div>

                                        <div className="flex justify-end gap-3 mt-6">
                                            <button
                                                onClick={() => setShowComponentPublishModal(false)}
                                                disabled={componentDefLoading}
                                                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleComponentPublishConfiguration}
                                                disabled={componentDefLoading || !componentPublishForm.config_name}
                                                className="btn-primary"
                                            >
                                                {componentDefLoading ? 'Publishing...' : 'Publish Configuration'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </>
            )}
        </Layout>
    );
}

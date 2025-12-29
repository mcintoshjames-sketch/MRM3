import { useState, useEffect, useRef, Fragment } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import AdminMonitoringOverview from '../components/AdminMonitoringOverview';

// Interfaces
interface User {
    user_id: number;
    email: string;
    full_name: string;
}

interface Model {
    model_id: number;
    model_name: string;
    monitoring_manager_id?: number | null;
}

interface MonitoringTeam {
    team_id: number;
    name: string;
    description: string | null;
    is_active: boolean;
    member_count: number;
    plan_count: number;
    members?: User[];
    created_at?: string;
    updated_at?: string;
}

interface KpmRef {
    kpm_id: number;
    name: string;
    category_id: number;
    evaluation_type?: string;
}

interface PlanMetric {
    metric_id: number;
    plan_id: number;
    kpm_id: number;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
    is_active: boolean;
    kpm: KpmRef;
}

interface MonitoringPlan {
    plan_id: number;
    name: string;
    description: string | null;
    frequency: string;
    is_active: boolean;
    next_submission_due_date: string | null;
    next_report_due_date: string | null;
    team_name?: string | null;
    data_provider_name?: string | null;
    model_count?: number;
    metric_count?: number;
    version_count?: number;
    active_version_number?: number | null;
    has_unpublished_changes?: boolean;
    monitoring_team_id?: number | null;
    data_provider_user_id?: number | null;
    reporting_lead_days?: number;
    team?: MonitoringTeam | null;
    data_provider?: User | null;
    models?: Model[];
    metrics?: PlanMetric[];
}

interface PlanVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    description: string | null;
    effective_date: string;
    published_by_name: string | null;
    published_at: string;
    is_active: boolean;
    metrics_count: number;
    cycles_count: number;
}

interface MetricSnapshot {
    snapshot_id: number;
    kpm_id: number;
    kpm_name: string;
    kpm_category_name: string | null;
    evaluation_type: string;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
}

interface PlanVersionDetail extends PlanVersion {
    metric_snapshots: MetricSnapshot[];
}

interface ActiveCyclesWarning {
    warning: boolean;
    message: string;
    active_cycle_count: number;
}

interface Kpm {
    kpm_id: number;
    name: string;
    description: string | null;
    evaluation_type: 'Quantitative' | 'Qualitative' | 'Outcome Only';
}

interface KpmCategory {
    category_id: number;
    code: string;
    name: string;
    kpms: Kpm[];
}

type TabType = 'overview' | 'plans' | 'teams';

export default function MonitoringPlansPage() {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<TabType>('overview');

    // Teams state
    const [teams, setTeams] = useState<MonitoringTeam[]>([]);
    const [loadingTeams, setLoadingTeams] = useState(false);
    const [showTeamForm, setShowTeamForm] = useState(false);
    const [editingTeam, setEditingTeam] = useState<MonitoringTeam | null>(null);
    const [teamFormData, setTeamFormData] = useState({
        name: '',
        description: '',
        is_active: true,
        member_ids: [] as number[]
    });

    // Plans state
    const [plans, setPlans] = useState<MonitoringPlan[]>([]);
    const [loadingPlans, setLoadingPlans] = useState(false);
    const [showPlanForm, setShowPlanForm] = useState(false);
    const [editingPlan, setEditingPlan] = useState<MonitoringPlan | null>(null);
    const [planFormData, setPlanFormData] = useState({
        name: '',
        description: '',
        frequency: 'Quarterly',
        monitoring_team_id: null as number | null,
        data_provider_user_id: null as number | null,
        reporting_lead_days: 30,
        is_active: true,
        model_ids: [] as number[]
    });
    const [dataProviderSearch, setDataProviderSearch] = useState('');
    const [showDataProviderDropdown, setShowDataProviderDropdown] = useState(false);
    const [showQuickTeamModal, setShowQuickTeamModal] = useState(false);
    const [quickTeamFormData, setQuickTeamFormData] = useState({
        name: '',
        description: '',
        is_active: true,
        member_ids: [] as number[]
    });
    const [quickTeamError, setQuickTeamError] = useState<string | null>(null);
    const [savingQuickTeam, setSavingQuickTeam] = useState(false);

    // Reference data
    const [allUsers, setAllUsers] = useState<User[]>([]);
    const [allModels, setAllModels] = useState<Model[]>([]);
    const [kpmCategories, setKpmCategories] = useState<KpmCategory[]>([]);

    // Metrics management
    const [selectedPlanForMetrics, setSelectedPlanForMetrics] = useState<MonitoringPlan | null>(null);
    const [showMetricsModal, setShowMetricsModal] = useState(false);

    // Versions management
    const [selectedPlanForVersions, setSelectedPlanForVersions] = useState<MonitoringPlan | null>(null);
    const [showVersionsModal, setShowVersionsModal] = useState(false);

    const [error, setError] = useState<string | null>(null);
    const [peekTeamId, setPeekTeamId] = useState<number | null>(null);
    const [peekTeamMembers, setPeekTeamMembers] = useState<User[]>([]);
    const [loadingPeekTeamId, setLoadingPeekTeamId] = useState<number | null>(null);
    const [peekTeamError, setPeekTeamError] = useState<string | null>(null);
    const [peekPlanId, setPeekPlanId] = useState<number | null>(null);
    const [peekPlanModels, setPeekPlanModels] = useState<Model[]>([]);
    const [loadingPeekPlanId, setLoadingPeekPlanId] = useState<number | null>(null);
    const [peekPlanError, setPeekPlanError] = useState<string | null>(null);

    // URL parameters for pre-population
    const [searchParams, setSearchParams] = useSearchParams();
    const preselectedModelId = searchParams.get('model');
    const hasProcessedModelParam = useRef(false);

    // Fetch data on mount
    useEffect(() => {
        fetchTeams();
        fetchPlans();
        fetchReferenceData();
    }, []);

    // Handle pre-selected model from URL parameter
    useEffect(() => {
        // Only process once to avoid re-triggering on re-renders
        if (preselectedModelId && allModels.length > 0 && !hasProcessedModelParam.current) {
            const modelId = parseInt(preselectedModelId, 10);
            const model = allModels.find(m => m.model_id === modelId);
            if (model) {
                hasProcessedModelParam.current = true;
                // Pre-populate form with the model and auto-open
                // If model has a monitoring_manager, default the data provider to that user
                setPlanFormData(prev => ({
                    ...prev,
                    name: `Monitoring Plan - ${model.model_name}`,
                    model_ids: [modelId],
                    data_provider_user_id: model.monitoring_manager_id || null
                }));
                setShowPlanForm(true);
                setActiveTab('plans');
                // Clear URL param after state is set (in next tick to avoid race)
                setTimeout(() => setSearchParams({}), 0);
            }
        }
    }, [preselectedModelId, allModels, setSearchParams]);

    useEffect(() => {
        if (!showPlanForm) return;
        if (!dataProviderSearch && planFormData.data_provider_user_id && allUsers.length > 0) {
            const selected = allUsers.find(
                (u) => u.user_id === planFormData.data_provider_user_id
            );
            if (selected) {
                setDataProviderSearch(selected.full_name || selected.email);
            }
        }
    }, [showPlanForm, dataProviderSearch, planFormData.data_provider_user_id, allUsers]);

    const fetchReferenceData = async () => {
        try {
            const [usersRes, modelsRes, kpmRes] = await Promise.all([
                api.get('/auth/users'),
                api.get('/models/'),
                api.get('/kpm/categories?active_only=false')
            ]);
            setAllUsers(usersRes.data);
            setAllModels(modelsRes.data);
            setKpmCategories(kpmRes.data);
        } catch (err) {
            console.error('Failed to fetch reference data:', err);
        }
    };

    // Teams CRUD
    const fetchTeams = async () => {
        setLoadingTeams(true);
        try {
            const response = await api.get('/monitoring/teams?include_inactive=true');
            setTeams(response.data);
        } catch (err) {
            console.error('Failed to fetch teams:', err);
        } finally {
            setLoadingTeams(false);
        }
    };

    const resetTeamForm = () => {
        setTeamFormData({ name: '', description: '', is_active: true, member_ids: [] });
        setEditingTeam(null);
        setShowTeamForm(false);
        setError(null);
    };

    const handleTeamSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            if (editingTeam) {
                await api.patch(`/monitoring/teams/${editingTeam.team_id}`, teamFormData);
            } else {
                await api.post('/monitoring/teams', teamFormData);
            }
            resetTeamForm();
            fetchTeams();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save team');
        }
    };

    const handleEditTeam = async (team: MonitoringTeam) => {
        // Fetch full team details to get members
        try {
            const response = await api.get(`/monitoring/teams/${team.team_id}`);
            const fullTeam = response.data;
            setEditingTeam(fullTeam);
            setTeamFormData({
                name: fullTeam.name,
                description: fullTeam.description || '',
                is_active: fullTeam.is_active,
                member_ids: fullTeam.members?.map((m: User) => m.user_id) || []
            });
            setShowTeamForm(true);
        } catch (err) {
            console.error('Failed to fetch team details:', err);
        }
    };

    const handleDeleteTeam = async (teamId: number) => {
        if (!confirm('Are you sure you want to delete this team? This cannot be undone.')) return;

        try {
            await api.delete(`/monitoring/teams/${teamId}`);
            fetchTeams();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete team');
        }
    };

    const handlePeekTeam = async (team: MonitoringTeam) => {
        if (peekTeamId === team.team_id) {
            setPeekTeamId(null);
            setPeekTeamMembers([]);
            setPeekTeamError(null);
            return;
        }
        setPeekTeamId(team.team_id);
        setPeekTeamMembers([]);
        setPeekTeamError(null);
        setLoadingPeekTeamId(team.team_id);
        try {
            const response = await api.get(`/monitoring/teams/${team.team_id}`);
            setPeekTeamMembers(response.data.members || []);
        } catch (err: any) {
            setPeekTeamError(err.response?.data?.detail || 'Failed to load team members');
        } finally {
            setLoadingPeekTeamId(null);
        }
    };

    const handlePeekPlanModels = async (plan: MonitoringPlan) => {
        if (peekPlanId === plan.plan_id) {
            setPeekPlanId(null);
            setPeekPlanModels([]);
            setPeekPlanError(null);
            return;
        }
        setPeekPlanId(plan.plan_id);
        setPeekPlanModels([]);
        setPeekPlanError(null);
        setLoadingPeekPlanId(plan.plan_id);
        try {
            const response = await api.get(`/monitoring/plans/${plan.plan_id}`);
            setPeekPlanModels(response.data.models || []);
        } catch (err: any) {
            setPeekPlanError(err.response?.data?.detail || 'Failed to load models');
        } finally {
            setLoadingPeekPlanId(null);
        }
    };

    // Plans CRUD
    const fetchPlans = async () => {
        setLoadingPlans(true);
        try {
            const response = await api.get('/monitoring/plans?include_inactive=true');
            setPlans(response.data);
        } catch (err) {
            console.error('Failed to fetch plans:', err);
        } finally {
            setLoadingPlans(false);
        }
    };

    const resetPlanForm = () => {
        setPlanFormData({
            name: '',
            description: '',
            frequency: 'Quarterly',
            monitoring_team_id: null,
            data_provider_user_id: null,
            reporting_lead_days: 30,
            is_active: true,
            model_ids: []
        });
        setDataProviderSearch('');
        setShowDataProviderDropdown(false);
        setShowQuickTeamModal(false);
        setQuickTeamFormData({
            name: '',
            description: '',
            is_active: true,
            member_ids: []
        });
        setQuickTeamError(null);
        setSavingQuickTeam(false);
        setEditingPlan(null);
        setShowPlanForm(false);
        setError(null);
    };

    const handlePlanSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            const payload = {
                ...planFormData,
                metrics: [] // Metrics are added separately
            };
            if (editingPlan) {
                await api.patch(`/monitoring/plans/${editingPlan.plan_id}`, payload);
            } else {
                await api.post('/monitoring/plans', payload);
            }
            resetPlanForm();
            fetchPlans();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save plan');
        }
    };

    const handleQuickAddTeam = async () => {
        const name = quickTeamFormData.name.trim();
        if (!name) {
            setQuickTeamError('Team name is required.');
            return;
        }
        const duplicate = teams.some(
            (team) => team.name.trim().toLowerCase() === name.toLowerCase()
        );
        if (duplicate) {
            setQuickTeamError('A monitoring team with this name already exists.');
            return;
        }
        setSavingQuickTeam(true);
        setQuickTeamError(null);
        try {
            const response = await api.post('/monitoring/teams', {
                name,
                description: quickTeamFormData.description.trim() || null,
                is_active: quickTeamFormData.is_active,
                member_ids: quickTeamFormData.member_ids
            });
            setPlanFormData((prev) => ({
                ...prev,
                monitoring_team_id: response.data.team_id
            }));
            setQuickTeamFormData({
                name: '',
                description: '',
                is_active: true,
                member_ids: []
            });
            setShowQuickTeamModal(false);
            fetchTeams();
        } catch (err: any) {
            setQuickTeamError(err.response?.data?.detail || 'Failed to add team');
        } finally {
            setSavingQuickTeam(false);
        }
    };

    const handleEditPlan = async (plan: MonitoringPlan) => {
        // Fetch full plan details
        try {
            const response = await api.get(`/monitoring/plans/${plan.plan_id}`);
            const fullPlan = response.data;
            setEditingPlan(fullPlan);
            setPlanFormData({
                name: fullPlan.name,
                description: fullPlan.description || '',
                frequency: fullPlan.frequency,
                monitoring_team_id: fullPlan.monitoring_team_id,
                data_provider_user_id: fullPlan.data_provider_user_id,
                reporting_lead_days: fullPlan.reporting_lead_days,
                is_active: fullPlan.is_active,
                model_ids: fullPlan.models?.map((m: Model) => m.model_id) || []
            });
            const selectedProvider = allUsers.find(
                (u) => u.user_id === fullPlan.data_provider_user_id
            );
            setDataProviderSearch(selectedProvider?.full_name || selectedProvider?.email || '');
            setShowPlanForm(true);
        } catch (err) {
            console.error('Failed to fetch plan details:', err);
        }
    };

    const handleDeletePlan = async (planId: number) => {
        if (!confirm('Are you sure you want to delete this monitoring plan? This cannot be undone.')) return;

        try {
            await api.delete(`/monitoring/plans/${planId}`);
            fetchPlans();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete plan');
        }
    };

    const openMetricsModal = async (plan: MonitoringPlan) => {
        try {
            const response = await api.get(`/monitoring/plans/${plan.plan_id}`);
            setSelectedPlanForMetrics(response.data);
            setShowMetricsModal(true);
        } catch (err) {
            console.error('Failed to fetch plan details:', err);
        }
    };

    const openVersionsModal = (plan: MonitoringPlan) => {
        setSelectedPlanForVersions(plan);
        setShowVersionsModal(true);
    };

    // Admin check
    if (user?.role !== 'Admin') {
        return (
            <Layout>
                <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-800">Access Denied</h2>
                    <p className="text-gray-600 mt-2">Only administrators can manage monitoring plans.</p>
                </div>
            </Layout>
        );
    }

    const selectedDataProvider = allUsers.find(
        (u) => u.user_id === planFormData.data_provider_user_id
    );
    const normalizedDataProviderSearch = dataProviderSearch.trim().toLowerCase();
    const filteredDataProviders = allUsers.filter((u) => {
        if (!normalizedDataProviderSearch) return true;
        return (
            u.full_name.toLowerCase().includes(normalizedDataProviderSearch) ||
            u.email.toLowerCase().includes(normalizedDataProviderSearch)
        );
    }).slice(0, 50);
    const sortedUsers = [...allUsers].sort((a, b) => {
        const nameA = a.full_name || a.email;
        const nameB = b.full_name || b.email;
        return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
    });
    const sortedPeekMembers = [...peekTeamMembers].sort((a, b) => {
        const nameA = a.full_name || a.email;
        const nameB = b.full_name || b.email;
        return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
    });
    const sortedPeekModels = [...peekPlanModels].sort((a, b) => {
        const nameA = a.model_name || '';
        const nameB = b.model_name || '';
        return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
    });

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Performance Monitoring</h2>
                    <p className="text-gray-600 text-sm mt-1">
                        Manage monitoring teams and plans for ongoing model monitoring
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="mb-6">
                <nav className="flex space-x-4 border-b border-gray-200">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`pb-3 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'overview'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('plans')}
                        className={`pb-3 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'plans'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Monitoring Plans
                    </button>
                    <button
                        onClick={() => setActiveTab('teams')}
                        className={`pb-3 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'teams'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Monitoring Teams
                    </button>
                </nav>
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <AdminMonitoringOverview />
            )}

            {/* Teams Tab */}
            {activeTab === 'teams' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-semibold">Monitoring Teams</h3>
                        <button onClick={() => setShowTeamForm(true)} className="btn-primary">
                            + Add Team
                        </button>
                    </div>

                    {showTeamForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h4 className="text-lg font-bold mb-4">
                                {editingTeam ? 'Edit Team' : 'Create New Team'}
                            </h4>

                            {error && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handleTeamSubmit}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Team Name *</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={teamFormData.name}
                                            onChange={(e) => setTeamFormData({ ...teamFormData, name: e.target.value })}
                                            placeholder="e.g., Credit Risk Monitoring Team"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Status</label>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={teamFormData.is_active}
                                                onChange={(e) => setTeamFormData({ ...teamFormData, is_active: e.target.checked })}
                                                className="mr-2"
                                            />
                                            <span>Active</span>
                                        </label>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Description</label>
                                    <textarea
                                        className="input-field"
                                        rows={2}
                                        value={teamFormData.description}
                                        onChange={(e) => setTeamFormData({ ...teamFormData, description: e.target.value })}
                                        placeholder="Optional description"
                                    />
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Team Members</label>
                                    <select
                                        multiple
                                        className="input-field h-32"
                                        value={teamFormData.member_ids.map(String)}
                                        onChange={(e) => {
                                            const selected = Array.from(e.target.selectedOptions, opt => parseInt(opt.value));
                                            setTeamFormData({ ...teamFormData, member_ids: selected });
                                        }}
                                    >
                                        {sortedUsers.map(u => (
                                            <option key={u.user_id} value={u.user_id}>
                                                {u.full_name} ({u.email})
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple</p>
                                </div>

                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">
                                        {editingTeam ? 'Update Team' : 'Create Team'}
                                    </button>
                                    <button type="button" onClick={resetTeamForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        {loadingTeams ? (
                            <div className="p-4 text-center">Loading teams...</div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Members</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plans</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {teams.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                                No monitoring teams. Click "Add Team" to create one.
                                            </td>
                                        </tr>
                                    ) : (
                                        teams.map((team) => (
                                            <Fragment key={team.team_id}>
                                                <tr className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 font-medium">{team.name}</td>
                                                    <td className="px-6 py-4 text-sm text-gray-600">{team.description || '-'}</td>
                                                    <td className="px-6 py-4">{team.member_count}</td>
                                                    <td className="px-6 py-4">{team.plan_count}</td>
                                                    <td className="px-6 py-4">
                                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                                            team.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                        }`}>
                                                            {team.is_active ? 'Active' : 'Inactive'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-right text-sm">
                                                        <button
                                                            onClick={() => handlePeekTeam(team)}
                                                            className="text-blue-600 hover:text-blue-800 mr-3"
                                                        >
                                                            {peekTeamId === team.team_id ? 'Hide' : 'Members'}
                                                        </button>
                                                        <button
                                                            onClick={() => handleEditTeam(team)}
                                                            className="text-blue-600 hover:text-blue-800 mr-3"
                                                        >
                                                            Edit
                                                        </button>
                                                        {team.plan_count === 0 && (
                                                            <button
                                                                onClick={() => handleDeleteTeam(team.team_id)}
                                                                className="text-red-600 hover:text-red-800"
                                                            >
                                                                Delete
                                                            </button>
                                                        )}
                                                    </td>
                                                </tr>
                                                {peekTeamId === team.team_id && (
                                                    <tr className="bg-gray-50">
                                                        <td colSpan={6} className="px-6 py-3 text-sm text-gray-700">
                                                            {loadingPeekTeamId === team.team_id && (
                                                                <div>Loading team members...</div>
                                                            )}
                                                            {loadingPeekTeamId !== team.team_id && peekTeamError && (
                                                                <div className="text-red-600">{peekTeamError}</div>
                                                            )}
                                                            {loadingPeekTeamId !== team.team_id && !peekTeamError && (
                                                                <div>
                                                                    <div className="font-medium mb-2">
                                                                        Team members for {team.name}
                                                                    </div>
                                                                    {sortedPeekMembers.length === 0 ? (
                                                                        <div className="text-gray-500">No members assigned.</div>
                                                                    ) : (
                                                                        <div className="flex flex-wrap gap-2">
                                                                            {sortedPeekMembers.map((member) => (
                                                                                <span
                                                                                    key={member.user_id}
                                                                                    className="bg-white border border-gray-200 rounded-full px-3 py-1 text-xs text-gray-700"
                                                                                >
                                                                                    {member.full_name} ({member.email})
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </td>
                                                    </tr>
                                                )}
                                            </Fragment>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}

            {/* Plans Tab */}
            {activeTab === 'plans' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-semibold">Monitoring Plans</h3>
                        <button onClick={() => setShowPlanForm(true)} className="btn-primary">
                            + Add Plan
                        </button>
                    </div>

                    {showPlanForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h4 className="text-lg font-bold mb-4">
                                {editingPlan ? 'Edit Plan' : 'Create New Plan'}
                            </h4>

                            {error && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handlePlanSubmit}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Plan Name *</label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            value={planFormData.name}
                                            onChange={(e) => setPlanFormData({ ...planFormData, name: e.target.value })}
                                            placeholder="e.g., Credit Risk Quarterly Monitoring"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Frequency *</label>
                                        <select
                                            className="input-field"
                                            value={planFormData.frequency}
                                            onChange={(e) => setPlanFormData({ ...planFormData, frequency: e.target.value })}
                                        >
                                            <option value="Monthly">Monthly</option>
                                            <option value="Quarterly">Quarterly</option>
                                            <option value="Semi-Annual">Semi-Annual</option>
                                            <option value="Annual">Annual</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Description</label>
                                    <textarea
                                        className="input-field"
                                        rows={2}
                                        value={planFormData.description}
                                        onChange={(e) => setPlanFormData({ ...planFormData, description: e.target.value })}
                                        placeholder="Optional description of the monitoring plan"
                                    />
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Monitoring Team</label>
                                        <select
                                            className="input-field"
                                            value={planFormData.monitoring_team_id || ''}
                                            onChange={(e) => setPlanFormData({
                                                ...planFormData,
                                                monitoring_team_id: e.target.value ? parseInt(e.target.value) : null
                                            })}
                                        >
                                            <option value="">-- Select Team --</option>
                                            {teams.filter(t => t.is_active).map(t => (
                                                <option key={t.team_id} value={t.team_id}>{t.name}</option>
                                            ))}
                                        </select>
                                        <div className="mt-2">
                                            <button
                                                type="button"
                                                className="text-sm text-blue-600 hover:text-blue-800"
                                                onClick={() => {
                                                    setQuickTeamError(null);
                                                    setQuickTeamFormData({
                                                        name: '',
                                                        description: '',
                                                        is_active: true,
                                                        member_ids: []
                                                    });
                                                    setShowQuickTeamModal(true);
                                                }}
                                            >
                                                + Add new team
                                            </button>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Data Provider</label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                className="input-field"
                                                placeholder="Type to search users..."
                                                value={dataProviderSearch}
                                                onChange={(e) => {
                                                    const value = e.target.value;
                                                    setDataProviderSearch(value);
                                                    setShowDataProviderDropdown(true);
                                                    if (!value) {
                                                        setPlanFormData({
                                                            ...planFormData,
                                                            data_provider_user_id: null
                                                        });
                                                        return;
                                                    }
                                                    if (planFormData.data_provider_user_id && selectedDataProvider) {
                                                        if (value !== selectedDataProvider.full_name && value !== selectedDataProvider.email) {
                                                            setPlanFormData({
                                                                ...planFormData,
                                                                data_provider_user_id: null
                                                            });
                                                        }
                                                    }
                                                }}
                                                onFocus={() => setShowDataProviderDropdown(true)}
                                                autoComplete="off"
                                            />
                                            {showDataProviderDropdown && (
                                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                    {filteredDataProviders.map((u) => (
                                                        <div
                                                            key={u.user_id}
                                                            className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                            onClick={() => {
                                                                setPlanFormData({
                                                                    ...planFormData,
                                                                    data_provider_user_id: u.user_id
                                                                });
                                                                setDataProviderSearch(u.full_name);
                                                                setShowDataProviderDropdown(false);
                                                            }}
                                                        >
                                                            <div className="font-medium">{u.full_name}</div>
                                                            <div className="text-xs text-gray-500">{u.email}</div>
                                                        </div>
                                                    ))}
                                                    {filteredDataProviders.length === 0 && (
                                                        <div className="px-4 py-2 text-sm text-gray-500">No users found</div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                        {planFormData.data_provider_user_id && selectedDataProvider && (
                                            <p className="mt-1 text-sm text-green-600">
                                                Selected: {selectedDataProvider.full_name}
                                            </p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Reporting Lead Days</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={planFormData.reporting_lead_days}
                                            onChange={(e) => setPlanFormData({
                                                ...planFormData,
                                                reporting_lead_days: parseInt(e.target.value) || 30
                                            })}
                                            min={1}
                                        />
                                        <p className="text-xs text-gray-500 mt-1">Days after submission for report</p>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">
                                        Models in Scope
                                    </label>
                                    <MultiSelectDropdown
                                        placeholder="Select Models"
                                        options={allModels.map(m => ({
                                            value: m.model_id,
                                            label: m.model_name,
                                            searchText: `${m.model_name} ${m.model_id}`,
                                            secondaryLabel: `ID: ${m.model_id}`
                                        }))}
                                        selectedValues={planFormData.model_ids}
                                        onChange={(values) => setPlanFormData({ ...planFormData, model_ids: values as number[] })}
                                    />
                                </div>

                                <div className="mb-4">
                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={planFormData.is_active}
                                            onChange={(e) => setPlanFormData({ ...planFormData, is_active: e.target.checked })}
                                            className="mr-2"
                                        />
                                        <span className="text-sm font-medium">Active</span>
                                    </label>
                                </div>

                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">
                                        {editingPlan ? 'Update Plan' : 'Create Plan'}
                                    </button>
                                    <button type="button" onClick={resetPlanForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {showQuickTeamModal && (
                        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                                    <h4 className="text-lg font-semibold">Create New Team</h4>
                                    <button
                                        type="button"
                                        className="text-gray-400 hover:text-gray-600"
                                        onClick={() => {
                                            setShowQuickTeamModal(false);
                                            setQuickTeamError(null);
                                        }}
                                    >
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                                <form
                                    className="px-6 py-4 space-y-4"
                                    onSubmit={(e) => {
                                        e.preventDefault();
                                        handleQuickAddTeam();
                                    }}
                                >
                                    {quickTeamError && (
                                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                                            {quickTeamError}
                                        </div>
                                    )}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium mb-2">Team Name *</label>
                                            <input
                                                type="text"
                                                className="input-field"
                                                value={quickTeamFormData.name}
                                                onChange={(e) => {
                                                    setQuickTeamFormData({ ...quickTeamFormData, name: e.target.value });
                                                    setQuickTeamError(null);
                                                }}
                                                placeholder="e.g., Credit Risk Monitoring Team"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium mb-2">Status</label>
                                            <label className="flex items-center">
                                                <input
                                                    type="checkbox"
                                                    checked={quickTeamFormData.is_active}
                                                    onChange={(e) => {
                                                        setQuickTeamFormData({ ...quickTeamFormData, is_active: e.target.checked });
                                                        setQuickTeamError(null);
                                                    }}
                                                    className="mr-2"
                                                />
                                                <span>Active</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Description</label>
                                        <textarea
                                            className="input-field"
                                            rows={2}
                                            value={quickTeamFormData.description}
                                            onChange={(e) => {
                                                setQuickTeamFormData({ ...quickTeamFormData, description: e.target.value });
                                                setQuickTeamError(null);
                                            }}
                                            placeholder="Optional description"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Team Members</label>
                                        <select
                                            multiple
                                            className="input-field h-32"
                                            value={quickTeamFormData.member_ids.map(String)}
                                            onChange={(e) => {
                                                const selected = Array.from(e.target.selectedOptions, opt => parseInt(opt.value));
                                                setQuickTeamFormData({ ...quickTeamFormData, member_ids: selected });
                                            }}
                                        >
                                            {sortedUsers.map(u => (
                                                <option key={u.user_id} value={u.user_id}>
                                                    {u.full_name} ({u.email})
                                                </option>
                                            ))}
                                        </select>
                                        <p className="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button type="submit" className="btn-primary" disabled={savingQuickTeam}>
                                            {savingQuickTeam ? 'Creating...' : 'Create Team'}
                                        </button>
                                        <button
                                            type="button"
                                            className="btn-secondary"
                                            onClick={() => {
                                                setShowQuickTeamModal(false);
                                                setQuickTeamError(null);
                                            }}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}

                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        {loadingPlans ? (
                            <div className="p-4 text-center">Loading plans...</div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frequency</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Models</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Metrics</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Versions</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Submission</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {plans.length === 0 ? (
                                        <tr>
                                            <td colSpan={9} className="px-6 py-4 text-center text-gray-500">
                                                No monitoring plans. Click "Add Plan" to create one.
                                            </td>
                                        </tr>
                                    ) : (
                                        plans.map((plan) => (
                                            <Fragment key={plan.plan_id}>
                                                <tr className="hover:bg-gray-50">
                                                    <td className="px-6 py-4">
                                                        <Link to={`/monitoring/${plan.plan_id}`} className="font-medium text-blue-600 hover:text-blue-800 hover:underline">
                                                            {plan.name}
                                                        </Link>
                                                        {plan.description && (
                                                            <div className="text-xs text-gray-500">{plan.description}</div>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4 text-sm">{plan.frequency}</td>
                                                    <td className="px-6 py-4 text-sm">{plan.team_name || '-'}</td>
                                                    <td className="px-6 py-4 text-sm">
                                                        <button
                                                            onClick={() => handlePeekPlanModels(plan)}
                                                            className="text-blue-600 hover:text-blue-800 underline"
                                                        >
                                                            {plan.model_count}
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-4 text-sm">
                                                        <button
                                                            onClick={() => openMetricsModal(plan)}
                                                            className="text-blue-600 hover:text-blue-800 underline"
                                                        >
                                                            {plan.metric_count} KPMs
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-4 text-sm">
                                                        <button
                                                            onClick={() => openVersionsModal(plan)}
                                                            className="text-blue-600 hover:text-blue-800 underline"
                                                        >
                                                            {plan.active_version_number
                                                                ? `v${plan.active_version_number}`
                                                                : 'None'}
                                                            {plan.version_count && plan.version_count > 0
                                                                ? ` (${plan.version_count})`
                                                                : ''}
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-4 text-sm">
                                                        {plan.next_submission_due_date || '-'}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                                            plan.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                        }`}>
                                                            {plan.is_active ? 'Active' : 'Inactive'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-right text-sm space-x-2">
                                                        <button
                                                            onClick={() => handleEditPlan(plan)}
                                                            className="text-blue-600 hover:text-blue-800"
                                                        >
                                                            Edit
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeletePlan(plan.plan_id)}
                                                            className="text-red-600 hover:text-red-800"
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                                {peekPlanId === plan.plan_id && (
                                                    <tr className="bg-gray-50">
                                                        <td colSpan={9} className="px-6 py-3 text-sm text-gray-700">
                                                            {loadingPeekPlanId === plan.plan_id && (
                                                                <div>Loading models...</div>
                                                            )}
                                                            {loadingPeekPlanId !== plan.plan_id && peekPlanError && (
                                                                <div className="text-red-600">{peekPlanError}</div>
                                                            )}
                                                            {loadingPeekPlanId !== plan.plan_id && !peekPlanError && (
                                                                <div>
                                                                    <div className="font-medium mb-2">
                                                                        Models in {plan.name}
                                                                    </div>
                                                                    {sortedPeekModels.length === 0 ? (
                                                                        <div className="text-gray-500">No models assigned.</div>
                                                                    ) : (
                                                                        <div className="flex flex-wrap gap-2">
                                                                            {sortedPeekModels.map((model) => (
                                                                                <span
                                                                                    key={model.model_id}
                                                                                    className="bg-white border border-gray-200 rounded-full px-3 py-1 text-xs text-gray-700"
                                                                                >
                                                                                    {model.model_name} (ID: {model.model_id})
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </td>
                                                    </tr>
                                                )}
                                            </Fragment>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}

            {/* Metrics Modal */}
            {showMetricsModal && selectedPlanForMetrics && (
                <MetricsModal
                    plan={selectedPlanForMetrics}
                    kpmCategories={kpmCategories}
                    onKpmCreated={fetchReferenceData}
                    onClose={() => {
                        setShowMetricsModal(false);
                        setSelectedPlanForMetrics(null);
                        fetchPlans(); // Refresh to update metric counts and has_unpublished_changes
                    }}
                />
            )}

            {showVersionsModal && selectedPlanForVersions && (
                <VersionsModal
                    plan={selectedPlanForVersions}
                    onClose={() => {
                        setShowVersionsModal(false);
                        setSelectedPlanForVersions(null);
                        fetchPlans(); // Refresh to update version counts and has_unpublished_changes
                    }}
                />
            )}
        </Layout>
    );
}

// Metrics Modal Component
interface MetricsModalProps {
    plan: MonitoringPlan;
    kpmCategories: KpmCategory[];
    onKpmCreated: () => Promise<void>;
    onClose: () => void;
}

function MetricsModal({ plan, kpmCategories, onKpmCreated, onClose }: MetricsModalProps) {
    const [metrics, setMetrics] = useState<PlanMetric[]>(plan.metrics || []);
    const [showAddForm, setShowAddForm] = useState(true);
    const [editingMetric, setEditingMetric] = useState<PlanMetric | null>(null);
    const [formData, setFormData] = useState({
        kpm_id: 0,
        yellow_min: '' as string | number,
        yellow_max: '' as string | number,
        red_min: '' as string | number,
        red_max: '' as string | number,
        qualitative_guidance: '',
        sort_order: 0,
        is_active: true
    });
    const [error, setError] = useState<string | null>(null);

    // Active cycles warning
    const [activeCyclesWarning, setActiveCyclesWarning] = useState<ActiveCyclesWarning | null>(null);

    useEffect(() => {
        // Fetch active cycles warning
        api.get(`/monitoring/plans/${plan.plan_id}/active-cycles-warning`)
            .then(res => setActiveCyclesWarning(res.data))
            .catch(err => console.error('Failed to fetch active cycles warning:', err));
    }, [plan.plan_id]);

    // Create New KPM inline state
    const [showCreateKpm, setShowCreateKpm] = useState(false);
    const [creatingKpm, setCreatingKpm] = useState(false);
    const [newKpmData, setNewKpmData] = useState({
        name: '',
        description: '',
        category_id: 0,
        evaluation_type: 'Quantitative' as 'Quantitative' | 'Qualitative' | 'Outcome Only',
        calculation: '',
        interpretation: ''
    });
    const [kpmError, setKpmError] = useState<string | null>(null);

    const resetForm = () => {
        setFormData({
            kpm_id: 0,
            yellow_min: '',
            yellow_max: '',
            red_min: '',
            red_max: '',
            qualitative_guidance: '',
            sort_order: metrics.length,
            is_active: true
        });
        setEditingMetric(null);
        setShowAddForm(false);
        setError(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        const payload = {
            kpm_id: formData.kpm_id,
            yellow_min: formData.yellow_min === '' ? null : parseFloat(String(formData.yellow_min)),
            yellow_max: formData.yellow_max === '' ? null : parseFloat(String(formData.yellow_max)),
            red_min: formData.red_min === '' ? null : parseFloat(String(formData.red_min)),
            red_max: formData.red_max === '' ? null : parseFloat(String(formData.red_max)),
            qualitative_guidance: formData.qualitative_guidance || null,
            sort_order: formData.sort_order,
            is_active: formData.is_active
        };

        try {
            if (editingMetric) {
                const response = await api.patch(
                    `/monitoring/plans/${plan.plan_id}/metrics/${editingMetric.metric_id}`,
                    payload
                );
                setMetrics(metrics.map(m =>
                    m.metric_id === editingMetric.metric_id ? response.data : m
                ));
            } else {
                const response = await api.post(
                    `/monitoring/plans/${plan.plan_id}/metrics`,
                    payload
                );
                setMetrics([...metrics, response.data]);
            }
            resetForm();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save metric');
        }
    };

    const handleEdit = (metric: PlanMetric) => {
        setEditingMetric(metric);
        setFormData({
            kpm_id: metric.kpm_id,
            yellow_min: metric.yellow_min ?? '',
            yellow_max: metric.yellow_max ?? '',
            red_min: metric.red_min ?? '',
            red_max: metric.red_max ?? '',
            qualitative_guidance: metric.qualitative_guidance || '',
            sort_order: metric.sort_order,
            is_active: metric.is_active
        });
        setShowAddForm(true);
    };

    const handleDelete = async (metricId: number) => {
        if (!confirm('Remove this metric from the plan?')) return;

        try {
            await api.delete(`/monitoring/plans/${plan.plan_id}/metrics/${metricId}`);
            setMetrics(metrics.filter(m => m.metric_id !== metricId));
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete metric');
        }
    };

    // Handle inline KPM creation
    const handleCreateKpm = async () => {
        setKpmError(null);
        setCreatingKpm(true);

        try {
            const response = await api.post('/kpm/kpms', {
                name: newKpmData.name,
                description: newKpmData.description || null,
                category_id: newKpmData.category_id,
                evaluation_type: newKpmData.evaluation_type,
                calculation: newKpmData.calculation || null,
                interpretation: newKpmData.interpretation || null,
                is_active: true,
                sort_order: 0
            });

            // Refresh the KPM categories to include the new KPM
            await onKpmCreated();

            // Auto-select the newly created KPM
            setFormData({ ...formData, kpm_id: response.data.kpm_id });

            // Reset and close the create KPM form
            setNewKpmData({
                name: '',
                description: '',
                category_id: 0,
                evaluation_type: 'Quantitative',
                calculation: '',
                interpretation: ''
            });
            setShowCreateKpm(false);
        } catch (err: any) {
            setKpmError(err.response?.data?.detail || 'Failed to create KPM');
        } finally {
            setCreatingKpm(false);
        }
    };

    // Get all KPMs from categories
    const allKpms = kpmCategories.flatMap(cat =>
        cat.kpms.map(kpm => ({ ...kpm, category_name: cat.name }))
    );

    // Filter out already-added KPMs unless editing
    const availableKpms = allKpms.filter(kpm =>
        editingMetric?.kpm_id === kpm.kpm_id || !metrics.some(m => m.kpm_id === kpm.kpm_id)
    );

    // Get the selected KPM's evaluation type
    const selectedKpm = allKpms.find(k => k.kpm_id === formData.kpm_id);
    const evaluationType = selectedKpm?.evaluation_type || 'Quantitative';

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                    <h3 className="text-lg font-bold">Metrics for: {plan.name}</h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 overflow-y-auto max-h-[70vh]">
                    <p className="text-sm text-gray-600 mb-4">
                        Configure thresholds and guidance for each KPM in this monitoring plan.
                    </p>

                    {/* Active Cycles Warning Banner */}
                    {activeCyclesWarning?.warning && (
                        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-4">
                            <div className="flex items-start gap-3">
                                <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                <div>
                                    <h4 className="font-medium text-amber-800">Active Cycles Warning</h4>
                                    <p className="text-sm text-amber-700 mt-1">{activeCyclesWarning.message}</p>
                                    <p className="text-xs text-amber-600 mt-2">
                                        {activeCyclesWarning.active_cycle_count} active cycle(s) are locked to previous versions and will not be affected by changes made here.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {showAddForm && (
                        <div className="bg-gray-50 p-4 rounded-lg mb-4 border">
                            <h4 className="font-medium mb-3">
                                {editingMetric ? 'Edit Metric' : 'Add Metric to Plan'}
                            </h4>

                            {error && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded mb-3 text-sm">
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handleSubmit}>
                                <div className="grid grid-cols-2 gap-4 mb-3">
                                    <div className="col-span-2">
                                        <div className="flex justify-between items-center mb-1">
                                            <label className="block text-sm font-medium">KPM *</label>
                                            {!editingMetric && !showCreateKpm && (
                                                <button
                                                    type="button"
                                                    onClick={() => setShowCreateKpm(true)}
                                                    className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    + Create New KPM
                                                </button>
                                            )}
                                        </div>

                                        {/* Inline Create New KPM Form */}
                                        {showCreateKpm && (
                                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                                                <div className="flex justify-between items-center mb-2">
                                                    <h5 className="text-sm font-medium text-blue-800">Create New KPM</h5>
                                                    <button
                                                        type="button"
                                                        onClick={() => setShowCreateKpm(false)}
                                                        className="text-blue-600 hover:text-blue-800"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                        </svg>
                                                    </button>
                                                </div>

                                                {kpmError && (
                                                    <div className="bg-red-100 border border-red-400 text-red-700 px-2 py-1 rounded mb-2 text-xs">
                                                        {kpmError}
                                                    </div>
                                                )}

                                                <div className="grid grid-cols-2 gap-2">
                                                    <div className="col-span-2">
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">Name *</label>
                                                        <input
                                                            type="text"
                                                            className="input-field text-sm"
                                                            value={newKpmData.name}
                                                            onChange={(e) => setNewKpmData({ ...newKpmData, name: e.target.value })}
                                                            placeholder="e.g., Population Stability Index"
                                                            required
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">Category *</label>
                                                        <select
                                                            className="input-field text-sm"
                                                            value={newKpmData.category_id}
                                                            onChange={(e) => setNewKpmData({ ...newKpmData, category_id: parseInt(e.target.value) })}
                                                            required
                                                        >
                                                            <option value={0}>-- Select Category --</option>
                                                            {kpmCategories.map(cat => (
                                                                <option key={cat.category_id} value={cat.category_id}>
                                                                    {cat.name}
                                                                </option>
                                                            ))}
                                                        </select>
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">Type *</label>
                                                        <select
                                                            className="input-field text-sm"
                                                            value={newKpmData.evaluation_type}
                                                            onChange={(e) => setNewKpmData({ ...newKpmData, evaluation_type: e.target.value as any })}
                                                        >
                                                            <option value="Quantitative">Quantitative (thresholds)</option>
                                                            <option value="Qualitative">Qualitative (judgment)</option>
                                                            <option value="Outcome Only">Outcome Only (R/Y/G)</option>
                                                        </select>
                                                    </div>
                                                    <div className="col-span-2">
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                                                        <textarea
                                                            className="input-field text-sm"
                                                            rows={2}
                                                            value={newKpmData.description}
                                                            onChange={(e) => setNewKpmData({ ...newKpmData, description: e.target.value })}
                                                            placeholder="Brief description of what this KPM measures..."
                                                        />
                                                    </div>
                                                    {newKpmData.evaluation_type === 'Quantitative' && (
                                                        <>
                                                            <div>
                                                                <label className="block text-xs font-medium text-gray-700 mb-1">Calculation</label>
                                                                <input
                                                                    type="text"
                                                                    className="input-field text-sm"
                                                                    value={newKpmData.calculation}
                                                                    onChange={(e) => setNewKpmData({ ...newKpmData, calculation: e.target.value })}
                                                                    placeholder="e.g., (Σ(pi - oi)²) / n"
                                                                />
                                                            </div>
                                                            <div>
                                                                <label className="block text-xs font-medium text-gray-700 mb-1">Interpretation</label>
                                                                <input
                                                                    type="text"
                                                                    className="input-field text-sm"
                                                                    value={newKpmData.interpretation}
                                                                    onChange={(e) => setNewKpmData({ ...newKpmData, interpretation: e.target.value })}
                                                                    placeholder="e.g., Lower is better"
                                                                />
                                                            </div>
                                                        </>
                                                    )}
                                                </div>

                                                <div className="flex gap-2 mt-3">
                                                    <button
                                                        type="button"
                                                        onClick={handleCreateKpm}
                                                        disabled={creatingKpm || !newKpmData.name || !newKpmData.category_id}
                                                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                                    >
                                                        {creatingKpm ? 'Creating...' : 'Create & Select'}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setShowCreateKpm(false)}
                                                        className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        <select
                                            className="input-field"
                                            value={formData.kpm_id}
                                            onChange={(e) => setFormData({ ...formData, kpm_id: parseInt(e.target.value) })}
                                            required
                                            disabled={!!editingMetric || showCreateKpm}
                                        >
                                            <option value={0}>-- Select KPM --</option>
                                            {availableKpms.map(kpm => (
                                                <option key={kpm.kpm_id} value={kpm.kpm_id}>
                                                    [{kpm.category_name}] {kpm.name} ({kpm.evaluation_type})
                                                </option>
                                            ))}
                                        </select>
                                        {selectedKpm && (
                                            <p className="text-xs text-gray-500 mt-1">
                                                Type: <span className={`font-medium ${
                                                    evaluationType === 'Quantitative' ? 'text-blue-600' :
                                                    evaluationType === 'Qualitative' ? 'text-purple-600' : 'text-green-600'
                                                }`}>{evaluationType}</span>
                                                {evaluationType === 'Quantitative' && ' - Configure numerical thresholds'}
                                                {evaluationType === 'Qualitative' && ' - Judgment-based assessment (R/Y/G outcome)'}
                                                {evaluationType === 'Outcome Only' && ' - Direct R/Y/G selection with notes'}
                                            </p>
                                        )}
                                    </div>

                                    {/* Only show threshold fields for Quantitative KPMs */}
                                    {evaluationType === 'Quantitative' && (
                                        <>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Yellow Min</label>
                                                <input
                                                    type="number"
                                                    step="any"
                                                    className="input-field"
                                                    value={formData.yellow_min}
                                                    onChange={(e) => setFormData({ ...formData, yellow_min: e.target.value })}
                                                    placeholder="e.g., 0.8"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Yellow Max</label>
                                                <input
                                                    type="number"
                                                    step="any"
                                                    className="input-field"
                                                    value={formData.yellow_max}
                                                    onChange={(e) => setFormData({ ...formData, yellow_max: e.target.value })}
                                                    placeholder="e.g., 0.9"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Red Min</label>
                                                <input
                                                    type="number"
                                                    step="any"
                                                    className="input-field"
                                                    value={formData.red_min}
                                                    onChange={(e) => setFormData({ ...formData, red_min: e.target.value })}
                                                    placeholder="e.g., 0.7"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Red Max</label>
                                                <input
                                                    type="number"
                                                    step="any"
                                                    className="input-field"
                                                    value={formData.red_max}
                                                    onChange={(e) => setFormData({ ...formData, red_max: e.target.value })}
                                                    placeholder="e.g., 0.7"
                                                />
                                            </div>
                                        </>
                                    )}

                                    <div className="col-span-2">
                                        <label className="block text-sm font-medium mb-1">
                                            {evaluationType === 'Quantitative' ? 'Additional Guidance' : 'Assessment Guidance *'}
                                        </label>
                                        <textarea
                                            className="input-field"
                                            rows={evaluationType === 'Quantitative' ? 2 : 4}
                                            value={formData.qualitative_guidance}
                                            onChange={(e) => setFormData({ ...formData, qualitative_guidance: e.target.value })}
                                            placeholder={
                                                evaluationType === 'Quantitative'
                                                    ? 'Additional guidance for interpreting this metric...'
                                                    : 'Describe the criteria for Green/Yellow/Red outcomes...'
                                            }
                                            required={evaluationType !== 'Quantitative'}
                                        />
                                        {evaluationType !== 'Quantitative' && (
                                            <p className="text-xs text-gray-500 mt-1">
                                                Define the rules or criteria for each outcome (Green/Yellow/Red)
                                            </p>
                                        )}
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-1">Sort Order</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={formData.sort_order}
                                            onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                                        />
                                    </div>
                                    <div className="flex items-end pb-2">
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={formData.is_active}
                                                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                                className="mr-2"
                                            />
                                            <span className="text-sm">Active</span>
                                        </label>
                                    </div>
                                </div>

                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary text-sm">
                                        {editingMetric ? 'Update Metric' : 'Add Metric to Plan'}
                                    </button>
                                    <button type="button" onClick={resetForm} className="btn-secondary text-sm">
                                        {editingMetric ? 'Cancel' : 'Clear'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Metrics Table */}
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">KPM</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Configuration</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {metrics.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500">
                                        No metrics configured. Use the form above to add metrics to this plan.
                                    </td>
                                </tr>
                            ) : (
                                metrics.sort((a, b) => a.sort_order - b.sort_order).map((metric) => {
                                    const kpmEvalType = metric.kpm.evaluation_type || 'Quantitative';
                                    const isQuantitative = kpmEvalType === 'Quantitative';

                                    return (
                                        <tr key={metric.metric_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-2">
                                                <div className="font-medium text-sm">{metric.kpm.name}</div>
                                                {metric.qualitative_guidance && (
                                                    <div className="text-xs text-gray-500 truncate max-w-xs" title={metric.qualitative_guidance}>
                                                        {metric.qualitative_guidance}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-2 text-sm">
                                                <span className={`px-2 py-0.5 text-xs rounded-full ${
                                                    kpmEvalType === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                    kpmEvalType === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                    'bg-green-100 text-green-800'
                                                }`}>
                                                    {kpmEvalType}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-sm">
                                                {isQuantitative ? (
                                                    <div className="flex gap-2">
                                                        <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">
                                                            Y: {metric.yellow_min ?? '-'} to {metric.yellow_max ?? '-'}
                                                        </span>
                                                        <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded text-xs">
                                                            R: {metric.red_min ?? '-'} to {metric.red_max ?? '-'}
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-gray-600 italic">
                                                        R/Y/G judgment-based
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-4 py-2">
                                                <span className={`px-2 py-0.5 text-xs rounded-full ${
                                                    metric.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                }`}>
                                                    {metric.is_active ? 'Active' : 'Inactive'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-right text-sm">
                                                <button
                                                    onClick={() => handleEdit(metric)}
                                                    className="text-blue-600 hover:text-blue-800 mr-2"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(metric.metric_id)}
                                                    className="text-red-600 hover:text-red-800"
                                                >
                                                    Remove
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="p-4 border-t bg-gray-50 flex justify-end">
                    <button onClick={onClose} className="btn-secondary">
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

// Versions Modal Component
interface VersionsModalProps {
    plan: MonitoringPlan;
    onClose: () => void;
}

function VersionsModal({ plan, onClose }: VersionsModalProps) {
    // Use backend-computed flag for unpublished changes
    const hasUnpublishedChanges = plan.has_unpublished_changes ?? false;
    const [versions, setVersions] = useState<PlanVersion[]>([]);
    const [loading, setLoading] = useState(true);
    const [showPublishForm, setShowPublishForm] = useState(false);
    const [publishFormData, setPublishFormData] = useState({
        version_name: '',
        description: '',
        effective_date: new Date().toISOString().split('T')[0]
    });
    const [publishing, setPublishing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Version detail view
    const [selectedVersion, setSelectedVersion] = useState<PlanVersionDetail | null>(null);
    const [loadingDetail, setLoadingDetail] = useState(false);

    useEffect(() => {
        fetchVersions();
    }, [plan.plan_id]);

    const fetchVersions = async () => {
        setLoading(true);
        try {
            const response = await api.get(`/monitoring/plans/${plan.plan_id}/versions`);
            setVersions(response.data);
        } catch (err) {
            console.error('Failed to fetch versions:', err);
        } finally {
            setLoading(false);
        }
    };

    const handlePublish = async (e: React.FormEvent) => {
        e.preventDefault();
        setPublishing(true);
        setError(null);

        try {
            await api.post(`/monitoring/plans/${plan.plan_id}/versions/publish`, {
                version_name: publishFormData.version_name || null,
                description: publishFormData.description || null,
                effective_date: publishFormData.effective_date || null
            });
            setShowPublishForm(false);
            setPublishFormData({
                version_name: '',
                description: '',
                effective_date: new Date().toISOString().split('T')[0]
            });
            fetchVersions();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to publish version');
        } finally {
            setPublishing(false);
        }
    };

    const handleViewDetail = async (version: PlanVersion) => {
        setLoadingDetail(true);
        try {
            const response = await api.get(`/monitoring/plans/${plan.plan_id}/versions/${version.version_id}`);
            setSelectedVersion(response.data);
        } catch (err) {
            console.error('Failed to fetch version details:', err);
        } finally {
            setLoadingDetail(false);
        }
    };

    const handleExportCSV = (version: PlanVersionDetail) => {
        // Create CSV content from metric snapshots
        const headers = ['KPM Name', 'Category', 'Type', 'Yellow Min', 'Yellow Max', 'Red Min', 'Red Max', 'Guidance'];
        const rows = version.metric_snapshots.map(s => [
            s.kpm_name,
            s.kpm_category_name || '',
            s.evaluation_type,
            s.yellow_min?.toString() || '',
            s.yellow_max?.toString() || '',
            s.red_min?.toString() || '',
            s.red_max?.toString() || '',
            (s.qualitative_guidance || '').replace(/"/g, '""')
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${plan.name}_v${version.version_number}_metrics_${version.effective_date}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                    <h3 className="text-lg font-bold">
                        {selectedVersion ? `Version ${selectedVersion.version_number} Details` : `Versions: ${plan.name}`}
                    </h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 overflow-y-auto max-h-[70vh]">
                    {/* Version Detail View */}
                    {selectedVersion ? (
                        <div>
                            <button
                                onClick={() => setSelectedVersion(null)}
                                className="text-blue-600 hover:text-blue-800 mb-4 flex items-center gap-1"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                </svg>
                                Back to Versions
                            </button>

                            <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <span className="text-sm text-gray-500">Version Name:</span>
                                        <p className="font-medium">{selectedVersion.version_name || `Version ${selectedVersion.version_number}`}</p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-gray-500">Effective Date:</span>
                                        <p className="font-medium">{selectedVersion.effective_date}</p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-gray-500">Published By:</span>
                                        <p className="font-medium">{selectedVersion.published_by_name || 'Unknown'}</p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-gray-500">Published At:</span>
                                        <p className="font-medium">{selectedVersion.published_at.split('T')[0]}</p>
                                    </div>
                                    {selectedVersion.description && (
                                        <div className="col-span-2">
                                            <span className="text-sm text-gray-500">Description:</span>
                                            <p className="font-medium">{selectedVersion.description}</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex justify-between items-center mb-2">
                                <h4 className="font-medium">Metric Snapshots ({selectedVersion.metric_snapshots.length})</h4>
                                <button
                                    onClick={() => handleExportCSV(selectedVersion)}
                                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Export CSV
                                </button>
                            </div>

                            <table className="min-w-full divide-y divide-gray-200 text-sm">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">KPM</th>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Thresholds</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {selectedVersion.metric_snapshots.length === 0 ? (
                                        <tr>
                                            <td colSpan={4} className="px-3 py-4 text-center text-gray-500">
                                                No metrics in this version snapshot.
                                            </td>
                                        </tr>
                                    ) : (
                                        selectedVersion.metric_snapshots.map(snapshot => (
                                            <tr key={snapshot.snapshot_id} className="hover:bg-gray-50">
                                                <td className="px-3 py-2">
                                                    <div className="font-medium">{snapshot.kpm_name}</div>
                                                    {snapshot.qualitative_guidance && (
                                                        <div className="text-xs text-gray-500 truncate max-w-xs" title={snapshot.qualitative_guidance}>
                                                            {snapshot.qualitative_guidance}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-3 py-2 text-gray-600">{snapshot.kpm_category_name || '-'}</td>
                                                <td className="px-3 py-2">
                                                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                                                        snapshot.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                        snapshot.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                        'bg-green-100 text-green-800'
                                                    }`}>
                                                        {snapshot.evaluation_type}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2">
                                                    {snapshot.evaluation_type === 'Quantitative' ? (
                                                        <div className="flex gap-1">
                                                            <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">
                                                                Y: {snapshot.yellow_min ?? '-'}/{snapshot.yellow_max ?? '-'}
                                                            </span>
                                                            <span className="px-1.5 py-0.5 bg-red-100 text-red-800 rounded text-xs">
                                                                R: {snapshot.red_min ?? '-'}/{snapshot.red_max ?? '-'}
                                                            </span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs text-gray-600 italic">Judgment-based</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        /* Version List View */
                        <div>
                            <div className="flex justify-between items-center mb-4">
                                <p className="text-sm text-gray-600">
                                    Manage version history for this monitoring plan. Each version captures a snapshot of the metric configuration.
                                </p>
                                {hasUnpublishedChanges && (
                                    <button
                                        onClick={() => setShowPublishForm(true)}
                                        className="btn-primary text-sm"
                                    >
                                        Publish New Version
                                    </button>
                                )}
                            </div>

                            {/* Unpublished Changes Warning */}
                            {hasUnpublishedChanges && !showPublishForm && (
                                <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-4">
                                    <div className="flex items-start gap-3">
                                        <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        <div>
                                            <h4 className="font-medium text-amber-800">Unpublished Changes</h4>
                                            <p className="text-sm text-amber-700 mt-1">
                                                Metrics or thresholds have been modified since the last published version.
                                                Publish a new version to make these changes available for future cycles.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Publish Form */}
                            {showPublishForm && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                                    <h4 className="font-medium text-blue-800 mb-3">Publish New Version</h4>
                                    <p className="text-sm text-blue-700 mb-3">
                                        This will create a snapshot of all current active metrics with their thresholds.
                                    </p>

                                    {error && (
                                        <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded mb-3 text-sm">
                                            {error}
                                        </div>
                                    )}

                                    <form onSubmit={handlePublish}>
                                        <div className="grid grid-cols-2 gap-4 mb-4">
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Version Name</label>
                                                <input
                                                    type="text"
                                                    className="input-field"
                                                    value={publishFormData.version_name}
                                                    onChange={(e) => setPublishFormData({ ...publishFormData, version_name: e.target.value })}
                                                    placeholder="e.g., Q4 2025 Threshold Update"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">Effective Date</label>
                                                <input
                                                    type="date"
                                                    className="input-field"
                                                    value={publishFormData.effective_date}
                                                    onChange={(e) => setPublishFormData({ ...publishFormData, effective_date: e.target.value })}
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-sm font-medium mb-1">Description/Changelog</label>
                                                <textarea
                                                    className="input-field"
                                                    rows={2}
                                                    value={publishFormData.description}
                                                    onChange={(e) => setPublishFormData({ ...publishFormData, description: e.target.value })}
                                                    placeholder="Describe what changed in this version..."
                                                />
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                type="submit"
                                                disabled={publishing}
                                                className="btn-primary text-sm disabled:opacity-50"
                                            >
                                                {publishing ? 'Publishing...' : 'Publish Version'}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setShowPublishForm(false);
                                                    setError(null);
                                                }}
                                                className="btn-secondary text-sm"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            )}

                            {/* Version List */}
                            {loading ? (
                                <div className="text-center py-8 text-gray-500">Loading versions...</div>
                            ) : versions.length === 0 ? (
                                <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                                    <p className="mb-2">No versions published yet.</p>
                                    <p className="text-sm">Click "Publish New Version" to create the first snapshot of your metric configuration.</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {versions.map(version => (
                                        <div
                                            key={version.version_id}
                                            className={`border rounded-lg p-4 ${version.is_active ? 'border-green-300 bg-green-50' : 'border-gray-200'}`}
                                        >
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-lg">v{version.version_number}</span>
                                                        {version.is_active && (
                                                            <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full">
                                                                Active
                                                            </span>
                                                        )}
                                                        {version.version_name && (
                                                            <span className="text-gray-600">{version.version_name}</span>
                                                        )}
                                                    </div>
                                                    <div className="text-sm text-gray-500 mt-1">
                                                        Published {version.published_at.split('T')[0]} by {version.published_by_name || 'Unknown'}
                                                    </div>
                                                    <div className="text-sm text-gray-600 mt-1">
                                                        Effective: {version.effective_date} | {version.metrics_count} metrics | {version.cycles_count} cycles using this version
                                                    </div>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleViewDetail(version)}
                                                        disabled={loadingDetail}
                                                        className="text-blue-600 hover:text-blue-800 text-sm"
                                                    >
                                                        View Details
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="p-4 border-t bg-gray-50 flex justify-end">
                    <button onClick={onClose} className="btn-secondary">
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

// Interfaces
interface AttestationCycle {
    cycle_id: number;
    cycle_name: string;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    status: 'PENDING' | 'OPEN' | 'CLOSED';
    opened_at: string | null;
    opened_by: { user_id: number; full_name: string } | null;
    closed_at: string | null;
    closed_by: { user_id: number; full_name: string } | null;
    notes: string | null;
    pending_count: number;
    submitted_count: number;
    accepted_count: number;
    rejected_count: number;
    total_count: number;
    completion_percentage: number;
}

interface CoverageTarget {
    target_id: number;
    risk_tier_id: number;
    target_percentage: string;
    is_blocking: boolean;
    effective_date: string;
    risk_tier: {
        value_id: number;
        code: string;
        label: string;
    };
}

interface SchedulingRule {
    rule_id: number;
    rule_name: string;
    rule_type: string;
    frequency: string;
    priority: number;
    is_active: boolean;
    owner_model_count_min: number | null;
    owner_high_fluctuation_flag: boolean | null;
    model_id: number | null;
    region_id: number | null;
    effective_date: string;
    model?: { model_id: number; model_name: string } | null;
    region?: { region_id: number; region_name: string } | null;
}

interface ModelOption {
    model_id: number;
    model_name: string;
}

interface RegionOption {
    region_id: number;
    region_name: string;
}

interface DashboardStats {
    pending_count: number;
    submitted_count: number;
    overdue_count: number;
    pending_changes: number;
    active_cycles: number;
}

interface CoverageByTier {
    risk_tier_code: string;
    risk_tier_label: string;
    total_models: number;
    attested_count: number;
    coverage_pct: number;
    target_pct: number;
    is_blocking: boolean;
    meets_target: boolean;
    gap: number;
}

interface CoverageReport {
    cycle_summary: AttestationCycle;
    coverage_by_tier: CoverageByTier[];
    overall_coverage_pct: number;
    blocking_gaps: string[];
}

interface AttestationRecord {
    attestation_id: number;
    cycle_id: number;
    cycle_name: string;
    model_id: number;
    model_name: string;
    risk_tier_code: string | null;
    owner_name: string;
    attesting_user_name: string;
    due_date: string;
    status: string;
    decision: string | null;
    attested_at: string | null;
    is_overdue: boolean;
    days_overdue: number;
}

interface UserWithFlag {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    high_fluctuation_flag: boolean;
}

type TabType = 'cycles' | 'rules' | 'targets' | 'review' | 'owners';
type FilterCycle = 'all' | number;

export default function AttestationCyclesPage() {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<TabType>('cycles');

    // Cycles state
    const [cycles, setCycles] = useState<AttestationCycle[]>([]);
    const [loadingCycles, setLoadingCycles] = useState(false);
    const [showCycleForm, setShowCycleForm] = useState(false);
    const [cycleFormData, setCycleFormData] = useState({
        cycle_name: '',
        period_start_date: '',
        period_end_date: '',
        submission_due_date: '',
        notes: ''
    });

    // Rules state
    const [rules, setRules] = useState<SchedulingRule[]>([]);
    const [loadingRules, setLoadingRules] = useState(false);
    const [showRuleForm, setShowRuleForm] = useState(false);
    const [editingRule, setEditingRule] = useState<SchedulingRule | null>(null);
    const [ruleFormData, setRuleFormData] = useState({
        rule_name: '',
        rule_type: 'GLOBAL_DEFAULT',
        frequency: 'ANNUAL',
        priority: 10,
        is_active: true,
        owner_model_count_min: null as number | null,
        owner_high_fluctuation_flag: null as boolean | null,
        model_id: null as number | null,
        region_id: null as number | null,
        effective_date: new Date().toISOString().split('T')[0]
    });
    const [models, setModels] = useState<ModelOption[]>([]);
    const [regions, setRegions] = useState<RegionOption[]>([]);

    // Targets state
    const [targets, setTargets] = useState<CoverageTarget[]>([]);
    const [loadingTargets, setLoadingTargets] = useState(false);
    const [editingTarget, setEditingTarget] = useState<CoverageTarget | null>(null);

    // Dashboard stats
    const [stats, setStats] = useState<DashboardStats | null>(null);

    // Coverage report for open cycle
    const [coverageReport, setCoverageReport] = useState<CoverageReport | null>(null);
    const [loadingCoverage, setLoadingCoverage] = useState(false);

    // Review queue state
    const [reviewRecords, setReviewRecords] = useState<AttestationRecord[]>([]);
    const [loadingReview, setLoadingReview] = useState(false);
    const [filterCycle, setFilterCycle] = useState<FilterCycle>('all');
    const [openCycles, setOpenCycles] = useState<{ cycle_id: number; cycle_name: string }[]>([]);

    // High fluctuation owners state
    const [highFluctuationOwners, setHighFluctuationOwners] = useState<UserWithFlag[]>([]);
    const [allUsers, setAllUsers] = useState<UserWithFlag[]>([]);
    const [loadingOwners, setLoadingOwners] = useState(false);
    const [ownerSearchQuery, setOwnerSearchQuery] = useState('');

    // Error/success messages
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Fetch data based on active tab
    useEffect(() => {
        if (activeTab === 'cycles') {
            fetchCycles();
            fetchStats();
        } else if (activeTab === 'rules') {
            fetchRules();
            fetchModels();
            fetchRegions();
        } else if (activeTab === 'targets') {
            fetchTargets();
        } else if (activeTab === 'review') {
            fetchReviewQueue();
            fetchStats();
        } else if (activeTab === 'owners') {
            fetchHighFluctuationOwners();
        }
    }, [activeTab]);

    // Fetch coverage report when cycles are loaded and there's an open cycle
    useEffect(() => {
        const openCycle = cycles.find(c => c.status === 'OPEN');
        if (openCycle) {
            fetchCoverageReport(openCycle.cycle_id);
        } else {
            setCoverageReport(null);
        }
    }, [cycles]);

    const fetchCycles = async () => {
        setLoadingCycles(true);
        try {
            const res = await api.get('/attestations/cycles');
            setCycles(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load cycles');
        } finally {
            setLoadingCycles(false);
        }
    };

    const fetchStats = async () => {
        try {
            const res = await api.get('/attestations/dashboard/stats');
            setStats(res.data);
        } catch (err: any) {
            console.error('Failed to load stats:', err);
        }
    };

    const fetchCoverageReport = async (cycleId: number) => {
        setLoadingCoverage(true);
        try {
            const res = await api.get(`/attestations/reports/coverage?cycle_id=${cycleId}`);
            setCoverageReport(res.data);
        } catch (err: any) {
            console.error('Failed to load coverage report:', err);
            setCoverageReport(null);
        } finally {
            setLoadingCoverage(false);
        }
    };

    const fetchRules = async () => {
        setLoadingRules(true);
        try {
            const res = await api.get('/attestations/rules');
            setRules(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load rules');
        } finally {
            setLoadingRules(false);
        }
    };

    const fetchModels = async () => {
        try {
            const res = await api.get('/models/?limit=500');
            setModels(res.data.items || res.data);
        } catch (err) {
            console.error('Failed to load models:', err);
        }
    };

    const fetchRegions = async () => {
        try {
            const res = await api.get('/regions/');
            setRegions(res.data);
        } catch (err) {
            console.error('Failed to load regions:', err);
        }
    };

    const fetchTargets = async () => {
        setLoadingTargets(true);
        try {
            const res = await api.get('/attestations/targets');
            setTargets(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load targets');
        } finally {
            setLoadingTargets(false);
        }
    };

    const fetchReviewQueue = async () => {
        setLoadingReview(true);
        try {
            const [recordsRes, cyclesRes] = await Promise.all([
                api.get('/attestations/records?status=SUBMITTED'),
                api.get('/attestations/cycles?status=OPEN')
            ]);
            setReviewRecords(recordsRes.data);
            setOpenCycles(cyclesRes.data.map((c: any) => ({ cycle_id: c.cycle_id, cycle_name: c.cycle_name })));
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load review queue');
        } finally {
            setLoadingReview(false);
        }
    };

    const fetchHighFluctuationOwners = async () => {
        setLoadingOwners(true);
        try {
            const res = await api.get('/auth/users');
            const users = res.data as UserWithFlag[];
            setAllUsers(users);
            setHighFluctuationOwners(users.filter(u => u.high_fluctuation_flag));
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load users');
        } finally {
            setLoadingOwners(false);
        }
    };

    const handleToggleHighFluctuation = async (userId: number, currentFlag: boolean) => {
        setError(null);
        try {
            await api.patch(`/auth/users/${userId}`, { high_fluctuation_flag: !currentFlag });
            setSuccess(currentFlag ? 'User removed from high fluctuation list' : 'User added to high fluctuation list');
            fetchHighFluctuationOwners();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update user');
        }
    };

    const filteredUsersForAdd = allUsers.filter(u =>
        !u.high_fluctuation_flag &&
        (ownerSearchQuery === '' ||
            u.full_name.toLowerCase().includes(ownerSearchQuery.toLowerCase()) ||
            u.email.toLowerCase().includes(ownerSearchQuery.toLowerCase()))
    );

    const filteredReviewRecords = reviewRecords.filter(r => {
        if (filterCycle === 'all') return true;
        return r.cycle_id === filterCycle;
    });

    const getDecisionBadge = (decision: string | null) => {
        switch (decision) {
            case 'I_ATTEST':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">I Attest</span>;
            case 'I_ATTEST_WITH_UPDATES':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">With Updates</span>;
            case 'OTHER':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">Other</span>;
            default:
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-500">-</span>;
        }
    };

    const getRiskTierBadge = (tier: string | null) => {
        if (!tier) return null;
        const colors: Record<string, string> = {
            'TIER_1': 'bg-red-100 text-red-800',
            'TIER_2': 'bg-orange-100 text-orange-800',
            'TIER_3': 'bg-yellow-100 text-yellow-800',
            'TIER_4': 'bg-green-100 text-green-800'
        };
        return (
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[tier] || 'bg-gray-100 text-gray-800'}`}>
                {tier.replace('_', ' ')}
            </span>
        );
    };

    const handleCreateCycle = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        try {
            await api.post('/attestations/cycles', cycleFormData);
            setSuccess('Cycle created successfully');
            setShowCycleForm(false);
            setCycleFormData({
                cycle_name: '',
                period_start_date: '',
                period_end_date: '',
                submission_due_date: '',
                notes: ''
            });
            fetchCycles();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create cycle');
        }
    };

    const handleOpenCycle = async (cycleId: number) => {
        setError(null);
        try {
            await api.post(`/attestations/cycles/${cycleId}/open`);
            setSuccess('Cycle opened successfully');
            fetchCycles();
            fetchStats();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to open cycle');
        }
    };

    const handleCloseCycle = async (cycleId: number) => {
        setError(null);
        try {
            await api.post(`/attestations/cycles/${cycleId}/close`);
            setSuccess('Cycle closed successfully');
            fetchCycles();
            fetchStats();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to close cycle');
        }
    };

    const handleUpdateTarget = async (tierId: number, targetPercentage: number, isBlocking: boolean) => {
        setError(null);
        try {
            await api.patch(`/attestations/targets/${tierId}`, {
                target_percentage: targetPercentage,
                is_blocking: isBlocking
            });
            setSuccess('Target updated successfully');
            setEditingTarget(null);
            fetchTargets();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update target');
        }
    };

    const resetRuleForm = () => {
        setRuleFormData({
            rule_name: '',
            rule_type: 'GLOBAL_DEFAULT',
            frequency: 'ANNUAL',
            priority: 10,
            is_active: true,
            owner_model_count_min: null,
            owner_high_fluctuation_flag: null,
            model_id: null,
            region_id: null,
            effective_date: new Date().toISOString().split('T')[0]
        });
        setEditingRule(null);
        setShowRuleForm(false);
    };

    const handleOpenRuleForm = (rule?: SchedulingRule) => {
        if (rule) {
            setEditingRule(rule);
            setRuleFormData({
                rule_name: rule.rule_name,
                rule_type: rule.rule_type,
                frequency: rule.frequency,
                priority: rule.priority,
                is_active: rule.is_active,
                owner_model_count_min: rule.owner_model_count_min,
                owner_high_fluctuation_flag: rule.owner_high_fluctuation_flag,
                model_id: rule.model_id,
                region_id: rule.region_id,
                effective_date: rule.effective_date.split('T')[0]
            });
        } else {
            resetRuleForm();
        }
        setShowRuleForm(true);
    };

    const handleSaveRule = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Build the payload based on rule type
        const payload: any = {
            rule_name: ruleFormData.rule_name,
            rule_type: ruleFormData.rule_type,
            frequency: ruleFormData.frequency,
            priority: ruleFormData.priority,
            is_active: ruleFormData.is_active,
            effective_date: ruleFormData.effective_date
        };

        // Add conditional fields based on rule type
        if (ruleFormData.rule_type === 'OWNER_THRESHOLD') {
            payload.owner_model_count_min = ruleFormData.owner_model_count_min;
            payload.owner_high_fluctuation_flag = ruleFormData.owner_high_fluctuation_flag;
        } else if (ruleFormData.rule_type === 'MODEL_OVERRIDE') {
            payload.model_id = ruleFormData.model_id;
        } else if (ruleFormData.rule_type === 'REGIONAL_OVERRIDE') {
            payload.region_id = ruleFormData.region_id;
        }

        try {
            if (editingRule) {
                await api.patch(`/attestations/rules/${editingRule.rule_id}`, {
                    rule_name: ruleFormData.rule_name,
                    frequency: ruleFormData.frequency,
                    priority: ruleFormData.priority,
                    is_active: ruleFormData.is_active,
                    owner_model_count_min: ruleFormData.owner_model_count_min,
                    owner_high_fluctuation_flag: ruleFormData.owner_high_fluctuation_flag
                });
                setSuccess('Rule updated successfully');
            } else {
                await api.post('/attestations/rules', payload);
                setSuccess('Rule created successfully');
            }
            resetRuleForm();
            fetchRules();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save rule');
        }
    };

    const handleDeleteRule = async (ruleId: number, ruleName: string) => {
        if (!window.confirm(`Are you sure you want to delete the rule "${ruleName}"?`)) {
            return;
        }
        setError(null);
        try {
            await api.delete(`/attestations/rules/${ruleId}`);
            setSuccess('Rule deleted successfully');
            fetchRules();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete rule');
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'OPEN':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Open</span>;
            case 'CLOSED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">Closed</span>;
            default:
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">Pending</span>;
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    if (user?.role !== 'Admin') {
        return (
            <Layout>
                <div className="text-center text-gray-500 py-8">
                    Access denied. Admin only.
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Attestation Management</h1>
                <p className="text-gray-600 mt-1">Manage attestation cycles, scheduling rules, and coverage targets</p>
            </div>

            {/* Messages */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">&times;</button>
                </div>
            )}
            {success && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded">
                    {success}
                    <button onClick={() => setSuccess(null)} className="float-right font-bold">&times;</button>
                </div>
            )}

            {/* Dashboard Stats */}
            {activeTab === 'cycles' && stats && (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500">Active Cycles</div>
                        <div className="text-2xl font-bold text-blue-600">{stats.active_cycles}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500">Pending</div>
                        <div className="text-2xl font-bold text-yellow-600">{stats.pending_count}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500">Submitted</div>
                        <div className="text-2xl font-bold text-blue-600">{stats.submitted_count}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500">Overdue</div>
                        <div className="text-2xl font-bold text-red-600">{stats.overdue_count}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500">Pending Changes</div>
                        <div className="text-2xl font-bold text-purple-600">{stats.pending_changes}</div>
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab('cycles')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'cycles'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Cycles
                    </button>
                    <button
                        onClick={() => setActiveTab('rules')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'rules'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Scheduling Rules
                    </button>
                    <button
                        onClick={() => setActiveTab('targets')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'targets'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Coverage Targets
                    </button>
                    <button
                        onClick={() => setActiveTab('review')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'review'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Review Queue
                        {stats && stats.submitted_count > 0 && (
                            <span className="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-blue-500 text-white">
                                {stats.submitted_count}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('owners')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'owners'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        High Fluctuation Owners
                        {highFluctuationOwners.length > 0 && (
                            <span className="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-orange-500 text-white">
                                {highFluctuationOwners.length}
                            </span>
                        )}
                    </button>
                </nav>
            </div>

            {/* Cycles Tab */}
            {activeTab === 'cycles' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">Attestation Cycles</h2>
                        <button
                            onClick={() => setShowCycleForm(true)}
                            className="btn-primary"
                        >
                            Create Cycle
                        </button>
                    </div>

                    {/* Create Cycle Form */}
                    {showCycleForm && (
                        <div className="bg-white p-6 rounded-lg shadow mb-6">
                            <h3 className="text-lg font-semibold mb-4">Create New Attestation Cycle</h3>
                            <form onSubmit={handleCreateCycle} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Cycle Name</label>
                                        <input
                                            type="text"
                                            required
                                            value={cycleFormData.cycle_name}
                                            onChange={(e) => setCycleFormData({ ...cycleFormData, cycle_name: e.target.value })}
                                            className="mt-1 input-field"
                                            placeholder="e.g., Q4 2025 Annual Attestation"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Submission Due Date</label>
                                        <input
                                            type="date"
                                            required
                                            value={cycleFormData.submission_due_date}
                                            onChange={(e) => setCycleFormData({ ...cycleFormData, submission_due_date: e.target.value })}
                                            className="mt-1 input-field"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Period Start Date</label>
                                        <input
                                            type="date"
                                            required
                                            value={cycleFormData.period_start_date}
                                            onChange={(e) => setCycleFormData({ ...cycleFormData, period_start_date: e.target.value })}
                                            className="mt-1 input-field"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Period End Date</label>
                                        <input
                                            type="date"
                                            required
                                            value={cycleFormData.period_end_date}
                                            onChange={(e) => setCycleFormData({ ...cycleFormData, period_end_date: e.target.value })}
                                            className="mt-1 input-field"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Notes (Optional)</label>
                                    <textarea
                                        value={cycleFormData.notes}
                                        onChange={(e) => setCycleFormData({ ...cycleFormData, notes: e.target.value })}
                                        className="mt-1 input-field"
                                        rows={2}
                                    />
                                </div>
                                <div className="flex space-x-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button
                                        type="button"
                                        onClick={() => setShowCycleForm(false)}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Cycles Table */}
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        {loadingCycles ? (
                            <div className="p-8 text-center text-gray-500">Loading...</div>
                        ) : cycles.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">No attestation cycles found</div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {cycles.map((cycle) => (
                                        <tr key={cycle.cycle_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/attestations/cycles/${cycle.cycle_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    {cycle.cycle_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(cycle.period_start_date)} to {formatDate(cycle.period_end_date)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(cycle.submission_due_date)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getStatusBadge(cycle.status)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center">
                                                    <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                                                        <div
                                                            className="bg-green-500 h-2 rounded-full"
                                                            style={{ width: `${cycle.completion_percentage}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-sm text-gray-600">
                                                        {cycle.completion_percentage.toFixed(0)}%
                                                    </span>
                                                </div>
                                                <div className="text-xs text-gray-400 mt-1">
                                                    {cycle.accepted_count}/{cycle.total_count} completed
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {cycle.status === 'PENDING' && (
                                                    <button
                                                        onClick={() => handleOpenCycle(cycle.cycle_id)}
                                                        className="text-green-600 hover:text-green-800 text-sm font-medium"
                                                    >
                                                        Open Cycle
                                                    </button>
                                                )}
                                                {cycle.status === 'OPEN' && (
                                                    <button
                                                        onClick={() => handleCloseCycle(cycle.cycle_id)}
                                                        className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                    >
                                                        Close Cycle
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Coverage vs. Targets Widget */}
                    {coverageReport && (
                        <div className="mt-6 bg-white rounded-lg shadow p-6">
                            <h3 className="text-lg font-semibold mb-4">Coverage vs. Targets</h3>
                            <div className="mb-4 text-sm text-gray-600">
                                Open Cycle: <span className="font-medium">{coverageReport.cycle_summary.cycle_name}</span>
                                {' | '}
                                Overall Coverage: <span className="font-medium">{coverageReport.overall_coverage_pct.toFixed(1)}%</span>
                            </div>

                            {loadingCoverage ? (
                                <div className="text-center py-4 text-gray-500">Loading coverage data...</div>
                            ) : (
                                <>
                                    <div className="overflow-x-auto">
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Models</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Attested</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Coverage</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Blocking</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {coverageReport.coverage_by_tier.map((tier) => (
                                                    <tr key={tier.risk_tier_code} className="hover:bg-gray-50">
                                                        <td className="px-4 py-3 whitespace-nowrap font-medium">{tier.risk_tier_label}</td>
                                                        <td className="px-4 py-3 whitespace-nowrap text-gray-600">{tier.total_models}</td>
                                                        <td className="px-4 py-3 whitespace-nowrap text-gray-600">{tier.attested_count}</td>
                                                        <td className="px-4 py-3 whitespace-nowrap">
                                                            <div className="flex items-center">
                                                                <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                                                    <div
                                                                        className={`h-2 rounded-full ${tier.meets_target ? 'bg-green-500' : 'bg-yellow-500'}`}
                                                                        style={{ width: `${Math.min(tier.coverage_pct, 100)}%` }}
                                                                    />
                                                                </div>
                                                                <span className="text-sm">{tier.coverage_pct.toFixed(1)}%</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3 whitespace-nowrap text-gray-600">{tier.target_pct}%</td>
                                                        <td className="px-4 py-3 whitespace-nowrap">
                                                            {tier.meets_target ? (
                                                                <span className="text-green-600 font-medium">✅ Met</span>
                                                            ) : (
                                                                <span className="text-yellow-600 font-medium">⚠️ Not Met ({tier.gap} pending)</span>
                                                            )}
                                                        </td>
                                                        <td className="px-4 py-3 whitespace-nowrap">
                                                            {tier.is_blocking ? (
                                                                <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">BLOCKING</span>
                                                            ) : (
                                                                <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">Advisory</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Blocking Gaps Warning */}
                                    {coverageReport.blocking_gaps.length > 0 && (
                                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                                            <h4 className="text-sm font-semibold text-red-800 mb-2">⚠️ Blocking Coverage Gaps</h4>
                                            <ul className="list-disc list-inside text-sm text-red-700">
                                                {coverageReport.blocking_gaps.map((gap, idx) => (
                                                    <li key={idx}>{gap}</li>
                                                ))}
                                            </ul>
                                            <p className="mt-2 text-xs text-red-600">
                                                These gaps must be resolved before closing the attestation cycle.
                                            </p>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}

                    {/* No Open Cycle Message */}
                    {!coverageReport && !loadingCoverage && cycles.length > 0 && !cycles.some(c => c.status === 'OPEN') && (
                        <div className="mt-6 bg-gray-50 rounded-lg p-6 text-center text-gray-500">
                            <p>No open attestation cycle. Open a cycle to view coverage data.</p>
                        </div>
                    )}
                </div>
            )}

            {/* Scheduling Rules Tab */}
            {activeTab === 'rules' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Scheduling Rules</h2>
                            <p className="text-sm text-gray-500">Rules determine attestation frequency for model owners</p>
                        </div>
                        <button onClick={() => handleOpenRuleForm()} className="btn-primary">
                            Create Rule
                        </button>
                    </div>

                    {/* Rule Form */}
                    {showRuleForm && (
                        <div className="bg-white p-6 rounded-lg shadow mb-6">
                            <h3 className="text-lg font-semibold mb-4">
                                {editingRule ? 'Edit Scheduling Rule' : 'Create Scheduling Rule'}
                            </h3>
                            <form onSubmit={handleSaveRule} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Rule Name *</label>
                                        <input
                                            type="text"
                                            required
                                            value={ruleFormData.rule_name}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, rule_name: e.target.value })}
                                            className="mt-1 input-field"
                                            placeholder="e.g., High-Volume Owners Quarterly"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Rule Type *</label>
                                        <select
                                            required
                                            value={ruleFormData.rule_type}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, rule_type: e.target.value })}
                                            className="mt-1 input-field"
                                            disabled={!!editingRule}
                                        >
                                            <option value="GLOBAL_DEFAULT">Global Default</option>
                                            <option value="OWNER_THRESHOLD">Owner Threshold</option>
                                            <option value="MODEL_OVERRIDE">Model Override</option>
                                            <option value="REGIONAL_OVERRIDE">Regional Override</option>
                                        </select>
                                        {editingRule && (
                                            <p className="text-xs text-gray-400 mt-1">Rule type cannot be changed</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Frequency *</label>
                                        <select
                                            required
                                            value={ruleFormData.frequency}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, frequency: e.target.value })}
                                            className="mt-1 input-field"
                                        >
                                            <option value="ANNUAL">Annual</option>
                                            <option value="QUARTERLY">Quarterly</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Priority</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="100"
                                            value={ruleFormData.priority}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, priority: parseInt(e.target.value) })}
                                            className="mt-1 input-field"
                                        />
                                        <p className="text-xs text-gray-400 mt-1">Higher priority rules win (1-100)</p>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Effective Date *</label>
                                        <input
                                            type="date"
                                            required
                                            value={ruleFormData.effective_date}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, effective_date: e.target.value })}
                                            className="mt-1 input-field"
                                            disabled={!!editingRule}
                                        />
                                    </div>
                                    <div className="flex items-center pt-6">
                                        <label className="flex items-center cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={ruleFormData.is_active}
                                                onChange={(e) => setRuleFormData({ ...ruleFormData, is_active: e.target.checked })}
                                                className="h-4 w-4 mr-2"
                                            />
                                            <span className="text-sm font-medium text-gray-700">Active</span>
                                        </label>
                                    </div>
                                </div>

                                {/* Conditional fields based on rule type */}
                                {ruleFormData.rule_type === 'OWNER_THRESHOLD' && (
                                    <div className="border-t pt-4">
                                        <h4 className="text-sm font-medium text-gray-700 mb-3">Owner Threshold Criteria</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700">Minimum Models Owned</label>
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={ruleFormData.owner_model_count_min ?? ''}
                                                    onChange={(e) => setRuleFormData({ ...ruleFormData, owner_model_count_min: e.target.value ? parseInt(e.target.value) : null })}
                                                    className="mt-1 input-field"
                                                    placeholder="e.g., 5"
                                                />
                                            </div>
                                            <div className="flex items-center pt-6">
                                                <label className="flex items-center cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        checked={ruleFormData.owner_high_fluctuation_flag ?? false}
                                                        onChange={(e) => setRuleFormData({ ...ruleFormData, owner_high_fluctuation_flag: e.target.checked || null })}
                                                        className="h-4 w-4 mr-2"
                                                    />
                                                    <span className="text-sm font-medium text-gray-700">High Fluctuation Flag Required</span>
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {ruleFormData.rule_type === 'MODEL_OVERRIDE' && !editingRule && (
                                    <div className="border-t pt-4">
                                        <h4 className="text-sm font-medium text-gray-700 mb-3">Model Override Settings</h4>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Select Model *</label>
                                            <select
                                                required
                                                value={ruleFormData.model_id ?? ''}
                                                onChange={(e) => setRuleFormData({ ...ruleFormData, model_id: e.target.value ? parseInt(e.target.value) : null })}
                                                className="mt-1 input-field"
                                            >
                                                <option value="">-- Select a Model --</option>
                                                {models.map((model) => (
                                                    <option key={model.model_id} value={model.model_id}>
                                                        {model.model_name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>
                                )}

                                {ruleFormData.rule_type === 'REGIONAL_OVERRIDE' && !editingRule && (
                                    <div className="border-t pt-4">
                                        <h4 className="text-sm font-medium text-gray-700 mb-3">Regional Override Settings</h4>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Select Region *</label>
                                            <select
                                                required
                                                value={ruleFormData.region_id ?? ''}
                                                onChange={(e) => setRuleFormData({ ...ruleFormData, region_id: e.target.value ? parseInt(e.target.value) : null })}
                                                className="mt-1 input-field"
                                            >
                                                <option value="">-- Select a Region --</option>
                                                {regions.map((region) => (
                                                    <option key={region.region_id} value={region.region_id}>
                                                        {region.region_name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>
                                )}

                                <div className="flex space-x-2 pt-4">
                                    <button type="submit" className="btn-primary">
                                        {editingRule ? 'Update Rule' : 'Create Rule'}
                                    </button>
                                    <button type="button" onClick={resetRuleForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        {loadingRules ? (
                            <div className="p-8 text-center text-gray-500">Loading...</div>
                        ) : rules.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">No scheduling rules configured</div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule Name</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frequency</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Criteria</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {rules.map((rule) => (
                                        <tr key={rule.rule_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap font-medium">{rule.rule_name}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {rule.rule_type.replace(/_/g, ' ')}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                                    rule.frequency === 'QUARTERLY'
                                                        ? 'bg-purple-100 text-purple-800'
                                                        : 'bg-blue-100 text-blue-800'
                                                }`}>
                                                    {rule.frequency}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {rule.priority}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {rule.rule_type === 'MODEL_OVERRIDE' && rule.model && (
                                                    <span>Model: {rule.model.model_name}</span>
                                                )}
                                                {rule.rule_type === 'REGIONAL_OVERRIDE' && rule.region && (
                                                    <span>Region: {rule.region.region_name}</span>
                                                )}
                                                {rule.rule_type === 'OWNER_THRESHOLD' && (
                                                    <>
                                                        {rule.owner_model_count_min && (
                                                            <span>Models &ge; {rule.owner_model_count_min}</span>
                                                        )}
                                                        {rule.owner_high_fluctuation_flag && (
                                                            <span className="ml-2 text-orange-600">High Fluctuation</span>
                                                        )}
                                                    </>
                                                )}
                                                {rule.rule_type === 'GLOBAL_DEFAULT' && (
                                                    <span className="text-gray-400">All owners</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                                    rule.is_active
                                                        ? 'bg-green-100 text-green-800'
                                                        : 'bg-gray-100 text-gray-800'
                                                }`}>
                                                    {rule.is_active ? 'Active' : 'Inactive'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <button
                                                    onClick={() => handleOpenRuleForm(rule)}
                                                    className="text-blue-600 hover:text-blue-800 text-sm font-medium mr-3"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteRule(rule.rule_id, rule.rule_name)}
                                                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}

            {/* Coverage Targets Tab */}
            {activeTab === 'targets' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">Coverage Targets by Risk Tier</h2>
                        <p className="text-sm text-gray-500">Blocking targets prevent cycle closure if not met</p>
                    </div>

                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        {loadingTargets ? (
                            <div className="p-8 text-center text-gray-500">Loading...</div>
                        ) : targets.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">No coverage targets configured</div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target %</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Blocking</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Effective Date</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {targets.map((target) => (
                                        <tr key={target.target_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap font-medium">
                                                {target.risk_tier.label}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {editingTarget?.target_id === target.target_id ? (
                                                    <input
                                                        type="number"
                                                        min="0"
                                                        max="100"
                                                        step="0.01"
                                                        defaultValue={parseFloat(target.target_percentage)}
                                                        className="input-field w-24"
                                                        id={`target-${target.target_id}`}
                                                    />
                                                ) : (
                                                    <span className="font-semibold text-blue-600">
                                                        {parseFloat(target.target_percentage).toFixed(0)}%
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {editingTarget?.target_id === target.target_id ? (
                                                    <input
                                                        type="checkbox"
                                                        defaultChecked={target.is_blocking}
                                                        id={`blocking-${target.target_id}`}
                                                        className="h-4 w-4"
                                                    />
                                                ) : (
                                                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                                        target.is_blocking
                                                            ? 'bg-red-100 text-red-800'
                                                            : 'bg-gray-100 text-gray-800'
                                                    }`}>
                                                        {target.is_blocking ? 'Yes' : 'No'}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(target.effective_date)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {editingTarget?.target_id === target.target_id ? (
                                                    <div className="flex space-x-2">
                                                        <button
                                                            onClick={() => {
                                                                const targetInput = document.getElementById(`target-${target.target_id}`) as HTMLInputElement;
                                                                const blockingInput = document.getElementById(`blocking-${target.target_id}`) as HTMLInputElement;
                                                                handleUpdateTarget(
                                                                    target.risk_tier_id,
                                                                    parseFloat(targetInput.value),
                                                                    blockingInput.checked
                                                                );
                                                            }}
                                                            className="text-green-600 hover:text-green-800 text-sm font-medium"
                                                        >
                                                            Save
                                                        </button>
                                                        <button
                                                            onClick={() => setEditingTarget(null)}
                                                            className="text-gray-600 hover:text-gray-800 text-sm"
                                                        >
                                                            Cancel
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        onClick={() => setEditingTarget(target)}
                                                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                                    >
                                                        Edit
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}

            {/* Review Queue Tab */}
            {activeTab === 'review' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Review Queue</h2>
                            <p className="text-sm text-gray-500">Review and approve submitted attestations</p>
                        </div>
                    </div>

                    {/* Stats Cards */}
                    {stats && (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                            <div className="bg-white p-4 rounded-lg shadow">
                                <div className="text-sm text-gray-500">Awaiting Review</div>
                                <div className="text-2xl font-bold text-blue-600">{stats.submitted_count}</div>
                            </div>
                            <div className="bg-white p-4 rounded-lg shadow">
                                <div className="text-sm text-gray-500">Pending Submission</div>
                                <div className="text-2xl font-bold text-yellow-600">{stats.pending_count}</div>
                            </div>
                            <div className="bg-white p-4 rounded-lg shadow">
                                <div className="text-sm text-gray-500">Overdue</div>
                                <div className="text-2xl font-bold text-red-600">{stats.overdue_count}</div>
                            </div>
                            <div className="bg-white p-4 rounded-lg shadow">
                                <div className="text-sm text-gray-500">Active Cycles</div>
                                <div className="text-2xl font-bold text-green-600">{stats.active_cycles}</div>
                            </div>
                        </div>
                    )}

                    {/* Filter */}
                    <div className="bg-white rounded-lg shadow p-4 mb-6">
                        <div className="flex items-center gap-4">
                            <label className="text-sm font-medium text-gray-700">Filter by Cycle:</label>
                            <select
                                value={filterCycle}
                                onChange={(e) => setFilterCycle(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
                                className="input-field w-auto"
                            >
                                <option value="all">All Open Cycles</option>
                                {openCycles.map(c => (
                                    <option key={c.cycle_id} value={c.cycle_id}>{c.cycle_name}</option>
                                ))}
                            </select>
                            <button
                                onClick={fetchReviewQueue}
                                className="btn-secondary ml-auto"
                            >
                                Refresh
                            </button>
                        </div>
                    </div>

                    {/* Review Queue Table */}
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        {loadingReview ? (
                            <div className="p-8 text-center text-gray-500">Loading...</div>
                        ) : filteredReviewRecords.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                No attestations awaiting review.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Attesting User</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submitted</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Decision</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {filteredReviewRecords.map((record) => (
                                        <tr key={record.attestation_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${record.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    {record.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getRiskTierBadge(record.risk_tier_code)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {record.attesting_user_name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {record.cycle_name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(record.attested_at)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getDecisionBadge(record.decision)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/attestations/${record.attestation_id}`}
                                                    className="btn-primary text-sm py-1 px-3"
                                                >
                                                    Review
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Help Text */}
                    <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h3 className="text-sm font-medium text-blue-800 mb-2">Review Guidelines</h3>
                        <ul className="text-sm text-blue-700 space-y-1">
                            <li>• Review all question responses and comments before accepting</li>
                            <li>• Pay special attention to "No" answers - ensure explanations are adequate</li>
                            <li>• Decisions with "I Attest with Updates" require review of proposed changes</li>
                            <li>• Provide clear feedback when rejecting an attestation</li>
                        </ul>
                    </div>
                </div>
            )}

            {/* High Fluctuation Owners Tab */}
            {activeTab === 'owners' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">High Fluctuation Owners</h2>
                            <p className="text-sm text-gray-500">Manage model owners flagged for quarterly attestation</p>
                        </div>
                    </div>

                    {/* Explanation Box */}
                    <div className="mb-6 bg-orange-50 border border-orange-200 rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-orange-800 mb-2">What is High Fluctuation?</h3>
                        <p className="text-sm text-orange-700 mb-3">
                            Model owners flagged as "High Fluctuation" have portfolios that change frequently (models added, removed, or transferred).
                            These owners are typically required to attest <strong>quarterly</strong> instead of annually to ensure
                            accurate model inventory records.
                        </p>
                        <ul className="text-sm text-orange-700 space-y-1">
                            <li>• This flag is used by scheduling rules to determine attestation frequency</li>
                            <li>• Owners can be added or removed from this list at any time</li>
                            <li>• Changes take effect on the next attestation cycle</li>
                        </ul>
                    </div>

                    {/* Current High Fluctuation Owners */}
                    <div className="bg-white rounded-lg shadow mb-6">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h3 className="text-md font-semibold text-gray-900">
                                Current High Fluctuation Owners ({highFluctuationOwners.length})
                            </h3>
                        </div>
                        {loadingOwners ? (
                            <div className="p-8 text-center text-gray-500">Loading...</div>
                        ) : highFluctuationOwners.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                No owners are currently flagged as high fluctuation.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {highFluctuationOwners.map((owner) => (
                                        <tr key={owner.user_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/users/${owner.user_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    {owner.full_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {owner.email}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {owner.role}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <button
                                                    onClick={() => handleToggleHighFluctuation(owner.user_id, true)}
                                                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                >
                                                    Remove
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Add New High Fluctuation Owner */}
                    <div className="bg-white rounded-lg shadow">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h3 className="text-md font-semibold text-gray-900">Add Owner to High Fluctuation List</h3>
                        </div>
                        <div className="p-4">
                            <div className="mb-4">
                                <input
                                    type="text"
                                    placeholder="Search by name or email..."
                                    value={ownerSearchQuery}
                                    onChange={(e) => setOwnerSearchQuery(e.target.value)}
                                    className="input-field w-full md:w-1/2"
                                />
                            </div>
                            {ownerSearchQuery && (
                                <div className="max-h-64 overflow-y-auto border rounded-lg">
                                    {filteredUsersForAdd.length === 0 ? (
                                        <div className="p-4 text-center text-gray-500 text-sm">
                                            No users found matching "{ownerSearchQuery}"
                                        </div>
                                    ) : (
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50 sticky top-0">
                                                <tr>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {filteredUsersForAdd.slice(0, 10).map((u) => (
                                                    <tr key={u.user_id} className="hover:bg-gray-50">
                                                        <td className="px-4 py-2 whitespace-nowrap text-sm font-medium">
                                                            {u.full_name}
                                                        </td>
                                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                                            {u.email}
                                                        </td>
                                                        <td className="px-4 py-2 whitespace-nowrap">
                                                            <button
                                                                onClick={() => {
                                                                    handleToggleHighFluctuation(u.user_id, false);
                                                                    setOwnerSearchQuery('');
                                                                }}
                                                                className="text-green-600 hover:text-green-800 text-sm font-medium"
                                                            >
                                                                Add
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                    {filteredUsersForAdd.length > 10 && (
                                        <div className="p-2 text-center text-xs text-gray-400 border-t">
                                            Showing first 10 results. Refine your search to see more.
                                        </div>
                                    )}
                                </div>
                            )}
                            {!ownerSearchQuery && (
                                <p className="text-sm text-gray-400">
                                    Start typing to search for users to add to the high fluctuation list.
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

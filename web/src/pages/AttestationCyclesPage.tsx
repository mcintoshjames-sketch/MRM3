import React, { useState, useEffect, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { canManageAttestations } from '../utils/roleUtils';
import api from '../api/client';
import Layout from '../components/Layout';
import StatFilterCard from '../components/StatFilterCard';

// Interfaces
interface AttestationCycle {
    cycle_id: number;
    cycle_name: string;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    status: 'PENDING' | 'OPEN' | 'UNDER_REVIEW' | 'CLOSED';
    opened_at: string | null;
    opened_by: { user_id: number; full_name: string } | null;
    closed_at: string | null;
    closed_by: { user_id: number; full_name: string } | null;
    notes: string | null;
    pending_count: number;
    submitted_count: number;
    accepted_count: number;
    rejected_count: number;
    total_records: number;
    coverage_pct: number;
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
    end_date: string | null;
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

interface AttestationQuestion {
    value_id: number;
    code: string;
    label: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
    frequency_scope: 'ANNUAL' | 'QUARTERLY' | 'BOTH';
    requires_comment_if_no: boolean;
}

interface AttestationChangeLink {
    link_id: number;
    attestation_id: number;
    change_type: 'MODEL_EDIT' | 'NEW_MODEL' | 'DECOMMISSION';
    model_id: number | null;
    pending_edit_id: number | null;
    decommissioning_request_id: number | null;
    created_at: string;
    attestation: {
        attestation_id: number;
        model: { model_id: number; model_name: string };
        owner: { user_id: number; full_name: string };
        cycle: { cycle_id: number; cycle_name: string };
    };
    model?: { model_id: number; model_name: string };
    pending_edit?: { pending_edit_id: number; status: string };
    decommissioning_request?: { request_id: number; status: string };
}

type TabType = 'cycles' | 'rules' | 'targets' | 'review' | 'owners' | 'all-records' | 'questions' | 'linked-changes';
type FilterCycle = 'all' | number;
type AllRecordsStatusFilter = 'all' | 'PENDING' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED' | 'OVERDUE';
type LinkedChangesFilter = 'all' | 'MODEL_EDIT' | 'NEW_MODEL' | 'DECOMMISSION';

interface GroupedByOwner {
    owner_id: number;
    owner_name: string;
    records: AttestationRecord[];
    total: number;
    pending: number;
    submitted: number;
    accepted: number;
    rejected: number;
    overdue: number;
}

export default function AttestationCyclesPage() {
    const { user } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();

    // Get initial tab from URL param or default to 'cycles'
    const tabParam = searchParams.get('tab');
    const validTabs: TabType[] = ['cycles', 'rules', 'targets', 'review', 'owners', 'all-records', 'questions', 'linked-changes'];
    const initialTab: TabType = tabParam && validTabs.includes(tabParam as TabType) ? (tabParam as TabType) : 'cycles';
    const [activeTab, setActiveTab] = useState<TabType>(initialTab);

    // Update URL when tab changes
    const handleTabChange = (tab: TabType) => {
        setActiveTab(tab);
        setSearchParams(tab === 'cycles' ? {} : { tab });
    };

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
        effective_date: new Date().toISOString().split('T')[0],
        end_date: null as string | null
    });
    const [models, setModels] = useState<ModelOption[]>([]);
    const [regions, setRegions] = useState<RegionOption[]>([]);
    const [modelSearchQuery, setModelSearchQuery] = useState('');
    const [showModelDropdown, setShowModelDropdown] = useState(false);

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

    // All Records tab state
    const [allRecords, setAllRecords] = useState<AttestationRecord[]>([]);
    const [loadingAllRecords, setLoadingAllRecords] = useState(false);
    const [allRecordsCycleFilter, setAllRecordsCycleFilter] = useState<number | null>(null);
    const [allRecordsStatusFilter, setAllRecordsStatusFilter] = useState<AllRecordsStatusFilter>('all');
    const [expandedOwners, setExpandedOwners] = useState<Set<number>>(new Set());

    // Questions tab state
    const [questions, setQuestions] = useState<AttestationQuestion[]>([]);
    const [loadingQuestions, setLoadingQuestions] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState<AttestationQuestion | null>(null);
    const [questionFormData, setQuestionFormData] = useState({
        label: '',
        description: '',
        sort_order: 0,
        is_active: true,
        frequency_scope: 'BOTH' as 'ANNUAL' | 'QUARTERLY' | 'BOTH',
        requires_comment_if_no: false
    });

    // Linked Changes tab state
    const [linkedChanges, setLinkedChanges] = useState<AttestationChangeLink[]>([]);
    const [loadingLinkedChanges, setLoadingLinkedChanges] = useState(false);
    const [linkedChangesCycleFilter, setLinkedChangesCycleFilter] = useState<number | null>(null);
    const [linkedChangesTypeFilter, setLinkedChangesTypeFilter] = useState<LinkedChangesFilter>('all');

    // Error/success messages
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Force Close modal state
    const [showForceCloseModal, setShowForceCloseModal] = useState(false);
    const [forceCloseCycleId, setForceCloseCycleId] = useState<number | null>(null);
    const [forceCloseReason, setForceCloseReason] = useState('');
    const [forceCloseBlockingGaps, setForceCloseBlockingGaps] = useState<string[]>([]);

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
        } else if (activeTab === 'all-records') {
            fetchCycles(); // Need cycles for dropdown
            fetchAllRecords();
        } else if (activeTab === 'questions') {
            fetchQuestions();
        } else if (activeTab === 'linked-changes') {
            fetchCycles(); // Need cycles for dropdown
            fetchLinkedChanges();
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

    const fetchAllRecords = async (cycleId?: number | null) => {
        setLoadingAllRecords(true);
        try {
            const params = new URLSearchParams();
            const targetCycleId = cycleId !== undefined ? cycleId : allRecordsCycleFilter;
            if (targetCycleId) {
                params.append('cycle_id', targetCycleId.toString());
            }
            const res = await api.get(`/attestations/records?${params.toString()}`);
            setAllRecords(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load attestation records');
        } finally {
            setLoadingAllRecords(false);
        }
    };

    const fetchQuestions = async () => {
        setLoadingQuestions(true);
        try {
            const res = await api.get('/attestations/questions/all');
            setQuestions(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load questions');
        } finally {
            setLoadingQuestions(false);
        }
    };

    const fetchLinkedChanges = async () => {
        setLoadingLinkedChanges(true);
        try {
            const params = linkedChangesCycleFilter ? { cycle_id: linkedChangesCycleFilter } : {};
            const res = await api.get('/attestations/admin/linked-changes', { params });
            setLinkedChanges(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load linked changes');
        } finally {
            setLoadingLinkedChanges(false);
        }
    };

    // Refetch linked changes when filter changes
    useEffect(() => {
        if (activeTab === 'linked-changes') {
            fetchLinkedChanges();
        }
    }, [linkedChangesCycleFilter]);

    const handleEditQuestion = (question: AttestationQuestion) => {
        setEditingQuestion(question);
        setQuestionFormData({
            label: question.label,
            description: question.description || '',
            sort_order: question.sort_order,
            is_active: question.is_active,
            frequency_scope: question.frequency_scope,
            requires_comment_if_no: question.requires_comment_if_no
        });
    };

    const handleSaveQuestion = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingQuestion) return;

        try {
            await api.patch(`/attestations/questions/${editingQuestion.value_id}`, questionFormData);
            setSuccess('Question updated successfully');
            setEditingQuestion(null);
            fetchQuestions();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update question');
        }
    };

    const resetQuestionForm = () => {
        setEditingQuestion(null);
        setQuestionFormData({
            label: '',
            description: '',
            sort_order: 0,
            is_active: true,
            frequency_scope: 'BOTH',
            requires_comment_if_no: false
        });
    };

    // Re-fetch records when cycle filter changes
    useEffect(() => {
        if (activeTab === 'all-records') {
            fetchAllRecords(allRecordsCycleFilter);
        }
    }, [allRecordsCycleFilter]);

    const baseAllRecords = useMemo(() => {
        if (!allRecordsCycleFilter) return allRecords;
        return allRecords.filter(record => record.cycle_id === allRecordsCycleFilter);
    }, [allRecords, allRecordsCycleFilter]);

    const filteredAllRecords = useMemo(() => {
        if (allRecordsStatusFilter === 'all') return baseAllRecords;
        if (allRecordsStatusFilter === 'OVERDUE') {
            return baseAllRecords.filter(record => record.is_overdue);
        }
        return baseAllRecords.filter(record => record.status === allRecordsStatusFilter);
    }, [baseAllRecords, allRecordsStatusFilter]);

    const {
        totalRecordsCount,
        pendingCount,
        submittedCount,
        acceptedCount,
        rejectedCount,
        overdueCount,
    } = useMemo(() => {
        return {
            totalRecordsCount: baseAllRecords.length,
            pendingCount: baseAllRecords.filter(r => r.status === 'PENDING').length,
            submittedCount: baseAllRecords.filter(r => r.status === 'SUBMITTED').length,
            acceptedCount: baseAllRecords.filter(r => r.status === 'ACCEPTED').length,
            rejectedCount: baseAllRecords.filter(r => r.status === 'REJECTED').length,
            overdueCount: baseAllRecords.filter(r => r.is_overdue).length,
        };
    }, [baseAllRecords]);

    // Group records by owner
    const groupedByOwner: GroupedByOwner[] = useMemo(() => {
        const groups: Record<string, GroupedByOwner> = {};

        filteredAllRecords.forEach(record => {
            const key = record.owner_name;
            if (!groups[key]) {
                groups[key] = {
                    owner_id: 0, // We don't have owner_id in AttestationRecord, use name as key
                    owner_name: record.owner_name,
                    records: [],
                    total: 0,
                    pending: 0,
                    submitted: 0,
                    accepted: 0,
                    rejected: 0,
                    overdue: 0
                };
            }
            groups[key].records.push(record);
            groups[key].total++;
            if (record.status === 'PENDING') groups[key].pending++;
            if (record.status === 'SUBMITTED') groups[key].submitted++;
            if (record.status === 'ACCEPTED') groups[key].accepted++;
            if (record.status === 'REJECTED') groups[key].rejected++;
            if (record.is_overdue) groups[key].overdue++;
        });

        return Object.values(groups).sort((a, b) => a.owner_name.localeCompare(b.owner_name));
    }, [filteredAllRecords]);

    const toggleOwnerExpanded = (ownerName: string) => {
        setExpandedOwners(prev => {
            const next = new Set(prev);
            // Use hash of owner name as numeric key
            const key = ownerName.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    const isOwnerExpanded = (ownerName: string): boolean => {
        const key = ownerName.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
        return expandedOwners.has(key);
    };

    const expandAllOwners = () => {
        const allKeys = new Set(groupedByOwner.map(g =>
            g.owner_name.split('').reduce((a, b) => a + b.charCodeAt(0), 0)
        ));
        setExpandedOwners(allKeys);
    };

    const collapseAllOwners = () => {
        setExpandedOwners(new Set());
    };

    const clearAllRecordsFilters = () => {
        setAllRecordsCycleFilter(null);
        setAllRecordsStatusFilter('all');
    };

    const clearLinkedChangesFilters = () => {
        setLinkedChangesCycleFilter(null);
        setLinkedChangesTypeFilter('all');
    };

    const toggleAllRecordsStatusFilter = (next: AllRecordsStatusFilter) => {
        setAllRecordsStatusFilter(prev => (prev === next ? 'all' : next));
    };

    const toggleLinkedChangesTypeFilter = (next: LinkedChangesFilter) => {
        setLinkedChangesTypeFilter(prev => (prev === next ? 'all' : next));
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

    const filteredLinkedChanges = useMemo(() => {
        if (linkedChangesTypeFilter === 'all') return linkedChanges;
        return linkedChanges.filter(link => link.change_type === linkedChangesTypeFilter);
    }, [linkedChanges, linkedChangesTypeFilter]);

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

    const hasAllRecordsFilters = allRecordsStatusFilter !== 'all' || allRecordsCycleFilter !== null;
    const hasLinkedChangesFilters = linkedChangesTypeFilter !== 'all' || linkedChangesCycleFilter !== null;

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
            const detail = err.response?.data?.detail || 'Failed to close cycle';
            // Check if error is due to blocking gaps (coverage targets not met)
            if (detail.toLowerCase().includes('blocking') || detail.toLowerCase().includes('cannot close')) {
                // Parse blocking gaps from the error message
                // Format: "Cannot close cycle: High Risk: X models missing (Y% < Z% target); ..."
                const gapMatches = detail.match(/([^:;]+: \d+ models? missing \([^)]+\))/g);
                const parsedGaps = gapMatches || ['Coverage targets not met - see details above'];

                // Show Force Close modal - no error banner needed since modal explains everything
                setForceCloseCycleId(cycleId);
                setForceCloseBlockingGaps(parsedGaps);
                setForceCloseReason('');
                setShowForceCloseModal(true);
            } else {
                setError(detail);
            }
        }
    };

    const handleForceCloseCycle = async () => {
        if (!forceCloseCycleId || !forceCloseReason.trim()) {
            setError('A reason is required to force close a cycle');
            return;
        }
        setError(null);
        try {
            await api.post(`/attestations/cycles/${forceCloseCycleId}/close?force=true`, {
                notes: `FORCE CLOSED: ${forceCloseReason}`
            });
            setSuccess('Cycle force closed successfully');
            setShowForceCloseModal(false);
            setForceCloseCycleId(null);
            setForceCloseReason('');
            setForceCloseBlockingGaps([]);
            fetchCycles();
            fetchStats();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to force close cycle');
        }
    };

    const cancelForceClose = () => {
        setShowForceCloseModal(false);
        setForceCloseCycleId(null);
        setForceCloseReason('');
        setForceCloseBlockingGaps([]);
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
            effective_date: new Date().toISOString().split('T')[0],
            end_date: null
        });
        setEditingRule(null);
        setShowRuleForm(false);
        setModelSearchQuery('');
        setShowModelDropdown(false);
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
                effective_date: rule.effective_date.split('T')[0],
                end_date: rule.end_date ? rule.end_date.split('T')[0] : null
            });
        } else {
            resetRuleForm();
        }
        setShowRuleForm(true);
    };

    const handleSaveRule = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Client-side validation for OWNER_THRESHOLD rules
        if (ruleFormData.rule_type === 'OWNER_THRESHOLD') {
            if (ruleFormData.owner_model_count_min === null && !ruleFormData.owner_high_fluctuation_flag) {
                setError('Owner Threshold rules must have at least one criterion (minimum models or high fluctuation flag)');
                return;
            }
        }

        // Build the payload based on rule type
        const payload: any = {
            rule_name: ruleFormData.rule_name,
            rule_type: ruleFormData.rule_type,
            frequency: ruleFormData.frequency,
            priority: ruleFormData.priority,
            is_active: ruleFormData.is_active,
            effective_date: ruleFormData.effective_date,
            end_date: ruleFormData.end_date
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
                    owner_high_fluctuation_flag: ruleFormData.owner_high_fluctuation_flag,
                    end_date: ruleFormData.end_date
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

    const handleDeactivateRule = async (ruleId: number, ruleName: string) => {
        if (!window.confirm(`Are you sure you want to deactivate the rule "${ruleName}"? The rule will be marked inactive but retained for audit purposes.`)) {
            return;
        }
        setError(null);
        try {
            await api.delete(`/attestations/rules/${ruleId}`);
            setSuccess('Rule deactivated successfully');
            fetchRules();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to deactivate rule');
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'OPEN':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Open</span>;
            case 'UNDER_REVIEW':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">Under Review</span>;
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

    if (!canManageAttestations(user)) {
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
                    <StatFilterCard
                        label="Active Cycles"
                        count={stats.active_cycles}
                        isActive={false}
                        onClick={() => {}}
                        colorScheme="blue"
                        disabled
                    />
                    <StatFilterCard
                        label="Pending"
                        count={stats.pending_count}
                        isActive={false}
                        onClick={() => {}}
                        colorScheme="yellow"
                        disabled
                    />
                    <StatFilterCard
                        label="Submitted"
                        count={stats.submitted_count}
                        isActive={false}
                        onClick={() => {}}
                        colorScheme="blue"
                        disabled
                    />
                    <StatFilterCard
                        label="Overdue"
                        count={stats.overdue_count}
                        isActive={false}
                        onClick={() => {}}
                        colorScheme="red"
                        disabled
                    />
                    <StatFilterCard
                        label="Pending Changes"
                        count={stats.pending_changes}
                        isActive={false}
                        onClick={() => {}}
                        colorScheme="purple"
                        disabled
                    />
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => handleTabChange('cycles')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'cycles'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Cycles
                    </button>
                    <button
                        onClick={() => handleTabChange('rules')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'rules'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Scheduling Rules
                    </button>
                    <button
                        onClick={() => handleTabChange('targets')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'targets'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Coverage Targets
                    </button>
                    <button
                        onClick={() => handleTabChange('review')}
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
                        onClick={() => handleTabChange('owners')}
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
                    <button
                        onClick={() => handleTabChange('all-records')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'all-records'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        All Records
                    </button>
                    <button
                        onClick={() => handleTabChange('questions')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'questions'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Questions
                    </button>
                    <button
                        onClick={() => handleTabChange('linked-changes')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'linked-changes'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Linked Changes
                        {linkedChanges.length > 0 && (
                            <span className="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-purple-500 text-white">
                                {linkedChanges.length}
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
                                            <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                                                {cycle.cycle_name}
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
                                                            style={{ width: `${cycle.coverage_pct}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-sm text-gray-600">
                                                        {cycle.coverage_pct.toFixed(0)}%
                                                    </span>
                                                </div>
                                                <div className="text-xs text-gray-400 mt-1">
                                                    {cycle.accepted_count}/{cycle.total_records} completed
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
                    {coverageReport?.cycle_summary && (
                        <div className="mt-6 bg-white rounded-lg shadow p-6">
                            <h3 className="text-lg font-semibold mb-4">Coverage vs. Targets</h3>
                            <div className="mb-4 text-sm text-gray-600">
                                Open Cycle: <span className="font-medium">{coverageReport.cycle_summary.cycle_name}</span>
                                {' | '}
                                Overall Coverage: <span className="font-medium">{coverageReport.overall_coverage_pct?.toFixed(1) ?? '0.0'}%</span>
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
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">End Date (Optional)</label>
                                        <input
                                            type="date"
                                            value={ruleFormData.end_date ?? ''}
                                            onChange={(e) => setRuleFormData({ ...ruleFormData, end_date: e.target.value || null })}
                                            className="mt-1 input-field"
                                            min={ruleFormData.effective_date}
                                        />
                                        <p className="text-xs text-gray-400 mt-1">Leave empty for no expiration</p>
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

                                {/* Help text for immutable fields when editing */}
                                {editingRule && (
                                    <div className="bg-gray-50 p-3 rounded text-sm text-gray-600">
                                        <strong>Note:</strong> Rule type, effective date, and target (model/region) cannot be changed after creation.
                                        To modify these, deactivate this rule and create a new one.
                                    </div>
                                )}

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
                                        <div className="relative">
                                            <label className="block text-sm font-medium text-gray-700">Search and Select Model *</label>
                                            <input
                                                type="text"
                                                placeholder="Type to search by name or ID..."
                                                value={modelSearchQuery}
                                                onChange={(e) => {
                                                    setModelSearchQuery(e.target.value);
                                                    setShowModelDropdown(true);
                                                }}
                                                onFocus={() => setShowModelDropdown(true)}
                                                className="mt-1 input-field"
                                            />
                                            {showModelDropdown && modelSearchQuery.length > 0 && (
                                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                    {models
                                                        .filter((model) =>
                                                            model.model_name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                                            String(model.model_id).includes(modelSearchQuery.toLowerCase())
                                                        )
                                                        .slice(0, 50)
                                                        .map((model) => (
                                                            <div
                                                                key={model.model_id}
                                                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                                onClick={() => {
                                                                    setRuleFormData({ ...ruleFormData, model_id: model.model_id });
                                                                    setModelSearchQuery(model.model_name);
                                                                    setShowModelDropdown(false);
                                                                }}
                                                            >
                                                                <div className="font-medium">{model.model_name}</div>
                                                                <div className="text-xs text-gray-500">ID: {model.model_id}</div>
                                                            </div>
                                                        ))}
                                                    {models.filter((model) =>
                                                        model.model_name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                                        String(model.model_id).includes(modelSearchQuery.toLowerCase())
                                                    ).length === 0 && (
                                                        <div className="px-4 py-2 text-sm text-gray-500">No models found</div>
                                                    )}
                                                </div>
                                            )}
                                            {ruleFormData.model_id && (
                                                <p className="mt-1 text-sm text-green-600">
                                                    ✓ Selected: {models.find(m => m.model_id === ruleFormData.model_id)?.model_name}
                                                </p>
                                            )}
                                            {!ruleFormData.model_id && modelSearchQuery.length > 0 && !showModelDropdown && (
                                                <p className="mt-1 text-sm text-amber-600">
                                                    Please select a model from the dropdown
                                                </p>
                                            )}
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
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date Window</th>
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
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(rule.effective_date)}
                                                {rule.end_date ? ` to ${formatDate(rule.end_date)}` : ' (no expiry)'}
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
                                                    onClick={() => handleDeactivateRule(rule.rule_id, rule.rule_name)}
                                                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                    title="Deactivates the rule (does not permanently delete)"
                                                >
                                                    Deactivate
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

            {/* All Records Tab */}
            {activeTab === 'all-records' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">All Attestation Records</h2>
                            <p className="text-sm text-gray-500">View all attestation records grouped by model owner</p>
                        </div>
                    </div>

                    {/* Filter and Controls */}
                    <div className="bg-white rounded-lg shadow p-4 mb-6">
                        <div className="flex flex-wrap items-center gap-4">
                            <div className="flex items-center gap-2">
                                <label className="text-sm font-medium text-gray-700">Filter by Cycle:</label>
                                <select
                                    value={allRecordsCycleFilter ?? ''}
                                    onChange={(e) => setAllRecordsCycleFilter(e.target.value ? parseInt(e.target.value) : null)}
                                    className="input-field w-auto"
                                >
                                    <option value="">All Cycles</option>
                                    {cycles.map(c => (
                                        <option key={c.cycle_id} value={c.cycle_id}>{c.cycle_name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex items-center gap-2 ml-auto">
                                {hasAllRecordsFilters && (
                                    <button
                                        type="button"
                                        onClick={clearAllRecordsFilters}
                                        className="btn-secondary text-sm"
                                    >
                                        Clear Filters
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={expandAllOwners}
                                    className="btn-secondary text-sm"
                                >
                                    Expand All
                                </button>
                                <button
                                    type="button"
                                    onClick={collapseAllOwners}
                                    className="btn-secondary text-sm"
                                >
                                    Collapse All
                                </button>
                                <button
                                    type="button"
                                    onClick={() => fetchAllRecords()}
                                    className="btn-secondary text-sm"
                                >
                                    Refresh
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
                        <StatFilterCard
                            label="Total Records"
                            count={totalRecordsCount}
                            isActive={allRecordsStatusFilter === 'all'}
                            onClick={() => setAllRecordsStatusFilter('all')}
                            colorScheme="blue"
                        />
                        <StatFilterCard
                            label="Pending"
                            count={pendingCount}
                            isActive={allRecordsStatusFilter === 'PENDING'}
                            onClick={() => toggleAllRecordsStatusFilter('PENDING')}
                            colorScheme="yellow"
                        />
                        <StatFilterCard
                            label="Submitted"
                            count={submittedCount}
                            isActive={allRecordsStatusFilter === 'SUBMITTED'}
                            onClick={() => toggleAllRecordsStatusFilter('SUBMITTED')}
                            colorScheme="purple"
                        />
                        <StatFilterCard
                            label="Accepted"
                            count={acceptedCount}
                            isActive={allRecordsStatusFilter === 'ACCEPTED'}
                            onClick={() => toggleAllRecordsStatusFilter('ACCEPTED')}
                            colorScheme="green"
                        />
                        <StatFilterCard
                            label="Rejected"
                            count={rejectedCount}
                            isActive={allRecordsStatusFilter === 'REJECTED'}
                            onClick={() => toggleAllRecordsStatusFilter('REJECTED')}
                            colorScheme="red"
                        />
                        <StatFilterCard
                            label="Overdue"
                            count={overdueCount}
                            isActive={allRecordsStatusFilter === 'OVERDUE'}
                            onClick={() => toggleAllRecordsStatusFilter('OVERDUE')}
                            colorScheme="red"
                        />
                    </div>

                    {/* Grouped by Owner */}
                    {loadingAllRecords ? (
                        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">Loading...</div>
                    ) : groupedByOwner.length === 0 ? (
                        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                            {allRecordsStatusFilter !== 'all'
                                ? 'No attestation records match the selected filters.'
                                : allRecordsCycleFilter
                                ? 'No attestation records found. Try selecting a different cycle.'
                                : 'Open a cycle to generate attestation records.'}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {groupedByOwner.map((group) => (
                                <div key={group.owner_name} className="bg-white rounded-lg shadow overflow-hidden">
                                    {/* Owner Header - Collapsible */}
                                    <button
                                        onClick={() => toggleOwnerExpanded(group.owner_name)}
                                        className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <span className="text-lg font-medium text-gray-900">
                                                {isOwnerExpanded(group.owner_name) ? '▼' : '▶'}
                                            </span>
                                            <span className="text-lg font-semibold text-gray-900">{group.owner_name}</span>
                                            <span className="text-sm text-gray-500">({group.total} models)</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {group.pending > 0 && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                                                    {group.pending} Pending
                                                </span>
                                            )}
                                            {group.submitted > 0 && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                                                    {group.submitted} Submitted
                                                </span>
                                            )}
                                            {group.accepted > 0 && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                                    {group.accepted} Accepted
                                                </span>
                                            )}
                                            {group.rejected > 0 && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
                                                    {group.rejected} Rejected
                                                </span>
                                            )}
                                            {group.overdue > 0 && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-500 text-white">
                                                    {group.overdue} Overdue
                                                </span>
                                            )}
                                        </div>
                                    </button>

                                    {/* Owner's Records Table - Expandable */}
                                    {isOwnerExpanded(group.owner_name) && (
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Decision</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Attested At</th>
                                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {group.records.map((record) => (
                                                    <tr key={record.attestation_id} className={`hover:bg-gray-50 ${record.is_overdue ? 'bg-red-50' : ''}`}>
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
                                                            {record.cycle_name}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                            <span className={record.is_overdue ? 'text-red-600 font-medium' : 'text-gray-500'}>
                                                                {formatDate(record.due_date)}
                                                            </span>
                                                            {record.is_overdue && (
                                                                <span className="ml-2 text-red-600 text-xs">
                                                                    ({record.days_overdue}d overdue)
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">
                                                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                                                record.status === 'ACCEPTED' ? 'bg-green-100 text-green-800' :
                                                                record.status === 'SUBMITTED' ? 'bg-blue-100 text-blue-800' :
                                                                record.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                                                                'bg-yellow-100 text-yellow-800'
                                                            }`}>
                                                                {record.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">
                                                            {getDecisionBadge(record.decision)}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {formatDate(record.attested_at)}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">
                                                            <Link
                                                                to={`/attestations/${record.attestation_id}`}
                                                                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                                            >
                                                                View
                                                            </Link>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Questions Tab */}
            {activeTab === 'questions' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold">Attestation Questions</h2>
                        <p className="text-sm text-gray-500">
                            Edit the questions shown in the attestation survey
                        </p>
                    </div>

                    {/* Edit Question Form */}
                    {editingQuestion && (
                        <div className="bg-white p-6 rounded-lg shadow mb-6">
                            <h3 className="text-lg font-semibold mb-4">Edit Question: {editingQuestion.code}</h3>
                            <form onSubmit={handleSaveQuestion} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">
                                        Question Text (Label)
                                    </label>
                                    <textarea
                                        value={questionFormData.label}
                                        onChange={(e) => setQuestionFormData({ ...questionFormData, label: e.target.value })}
                                        rows={3}
                                        className="mt-1 block w-full border rounded-md px-3 py-2"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">
                                        Description (Optional)
                                    </label>
                                    <textarea
                                        value={questionFormData.description}
                                        onChange={(e) => setQuestionFormData({ ...questionFormData, description: e.target.value })}
                                        rows={2}
                                        className="mt-1 block w-full border rounded-md px-3 py-2"
                                    />
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">
                                            Frequency Scope
                                        </label>
                                        <select
                                            value={questionFormData.frequency_scope}
                                            onChange={(e) => setQuestionFormData({ ...questionFormData, frequency_scope: e.target.value as 'ANNUAL' | 'QUARTERLY' | 'BOTH' })}
                                            className="mt-1 block w-full border rounded-md px-3 py-2"
                                        >
                                            <option value="BOTH">Both (Annual & Quarterly)</option>
                                            <option value="ANNUAL">Annual Only</option>
                                            <option value="QUARTERLY">Quarterly Only</option>
                                        </select>
                                        <p className="text-xs text-gray-500 mt-1">When this question appears</p>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">
                                            Sort Order
                                        </label>
                                        <input
                                            type="number"
                                            value={questionFormData.sort_order}
                                            onChange={(e) => setQuestionFormData({ ...questionFormData, sort_order: parseInt(e.target.value) || 0 })}
                                            className="mt-1 block w-full border rounded-md px-3 py-2"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center">
                                            <input
                                                type="checkbox"
                                                id="is_active"
                                                checked={questionFormData.is_active}
                                                onChange={(e) => setQuestionFormData({ ...questionFormData, is_active: e.target.checked })}
                                                className="mr-2"
                                            />
                                            <label htmlFor="is_active" className="text-sm text-gray-700">Active</label>
                                        </div>
                                        <div className="flex items-center">
                                            <input
                                                type="checkbox"
                                                id="requires_comment"
                                                checked={questionFormData.requires_comment_if_no}
                                                onChange={(e) => setQuestionFormData({ ...questionFormData, requires_comment_if_no: e.target.checked })}
                                                className="mr-2"
                                            />
                                            <label htmlFor="requires_comment" className="text-sm text-gray-700">Require comment if "No"</label>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Save Changes</button>
                                    <button type="button" onClick={resetQuestionForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Questions Table */}
                    {loadingQuestions ? (
                        <div className="text-center py-4">Loading questions...</div>
                    ) : (
                        <div className="bg-white rounded-lg shadow overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Order
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Code
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" style={{ maxWidth: '400px' }}>
                                            Question Text
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Frequency
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Comment Required
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {questions.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                                                No attestation questions found.
                                            </td>
                                        </tr>
                                    ) : (
                                        questions.map((q) => (
                                            <tr key={q.value_id} className={!q.is_active ? 'bg-gray-50' : ''}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {q.sort_order}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {q.code}
                                                </td>
                                                <td className="px-6 py-4 text-sm text-gray-900" style={{ maxWidth: '400px' }}>
                                                    <div className="truncate" title={q.label}>
                                                        {q.label}
                                                    </div>
                                                    {q.description && (
                                                        <div className="text-xs text-gray-500 truncate" title={q.description}>
                                                            {q.description}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        q.frequency_scope === 'BOTH' ? 'bg-purple-100 text-purple-800' :
                                                        q.frequency_scope === 'ANNUAL' ? 'bg-blue-100 text-blue-800' :
                                                        'bg-green-100 text-green-800'
                                                    }`}>
                                                        {q.frequency_scope}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {q.requires_comment_if_no ? (
                                                        <span className="text-orange-600 font-medium">Yes</span>
                                                    ) : (
                                                        <span className="text-gray-400">No</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        q.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                        {q.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                    <button
                                                        onClick={() => handleEditQuestion(q)}
                                                        className="text-blue-600 hover:text-blue-800 font-medium"
                                                    >
                                                        Edit
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}

                    <div className="mt-4 text-sm text-gray-500">
                        <p><strong>Note:</strong> Question codes cannot be changed. To add a new question, use the Taxonomy page to add a value to the "Attestation Question" taxonomy.</p>
                    </div>
                </div>
            )}

            {/* Linked Changes Tab */}
            {activeTab === 'linked-changes' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Linked Inventory Changes</h2>
                            <p className="text-sm text-gray-500">View all inventory changes linked to attestation records</p>
                        </div>
                    </div>

                    {/* Filter */}
                    <div className="bg-white rounded-lg shadow p-4 mb-6">
                        <div className="flex flex-wrap items-center gap-4">
                            <div className="flex items-center gap-2">
                                <label className="text-sm font-medium text-gray-700">Filter by Cycle:</label>
                                <select
                                    value={linkedChangesCycleFilter ?? ''}
                                    onChange={(e) => setLinkedChangesCycleFilter(e.target.value ? parseInt(e.target.value) : null)}
                                    className="input-field w-auto"
                                >
                                    <option value="">All Cycles</option>
                                    {cycles.map(c => (
                                        <option key={c.cycle_id} value={c.cycle_id}>{c.cycle_name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex items-center gap-2 ml-auto">
                                {hasLinkedChangesFilters && (
                                    <button
                                        type="button"
                                        onClick={clearLinkedChangesFilters}
                                        className="btn-secondary text-sm"
                                    >
                                        Clear Filters
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={() => fetchLinkedChanges()}
                                    className="btn-secondary text-sm"
                                >
                                    Refresh
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <button
                            type="button"
                            aria-pressed={linkedChangesTypeFilter === 'all'}
                            onClick={() => toggleLinkedChangesTypeFilter('all')}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 ${
                                linkedChangesTypeFilter === 'all' ? 'ring-2 ring-gray-400' : ''
                            }`}
                        >
                            <div className="text-sm text-gray-500">Total Links</div>
                            <div className="text-2xl font-bold text-gray-900">{linkedChanges.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={linkedChangesTypeFilter === 'MODEL_EDIT'}
                            onClick={() => toggleLinkedChangesTypeFilter('MODEL_EDIT')}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                                linkedChangesTypeFilter === 'MODEL_EDIT' ? 'ring-2 ring-blue-500' : ''
                            }`}
                        >
                            <div className="text-sm text-gray-500">Model Edits</div>
                            <div className="text-2xl font-bold text-blue-600">
                                {linkedChanges.filter(l => l.change_type === 'MODEL_EDIT').length}
                            </div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={linkedChangesTypeFilter === 'NEW_MODEL'}
                            onClick={() => toggleLinkedChangesTypeFilter('NEW_MODEL')}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
                                linkedChangesTypeFilter === 'NEW_MODEL' ? 'ring-2 ring-green-500' : ''
                            }`}
                        >
                            <div className="text-sm text-gray-500">New Models</div>
                            <div className="text-2xl font-bold text-green-600">
                                {linkedChanges.filter(l => l.change_type === 'NEW_MODEL').length}
                            </div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={linkedChangesTypeFilter === 'DECOMMISSION'}
                            onClick={() => toggleLinkedChangesTypeFilter('DECOMMISSION')}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                                linkedChangesTypeFilter === 'DECOMMISSION' ? 'ring-2 ring-red-500' : ''
                            }`}
                        >
                            <div className="text-sm text-gray-500">Decommissions</div>
                            <div className="text-2xl font-bold text-red-600">
                                {linkedChanges.filter(l => l.change_type === 'DECOMMISSION').length}
                            </div>
                        </button>
                    </div>

                    {/* Linked Changes Table */}
                    {loadingLinkedChanges ? (
                        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">Loading...</div>
                    ) : filteredLinkedChanges.length === 0 ? (
                        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                            {linkedChangesTypeFilter !== 'all'
                                ? 'No linked changes match the selected filters.'
                                : linkedChangesCycleFilter
                                ? 'No linked changes found. Try selecting a different cycle.'
                                : 'Linked changes will appear here when model owners make inventory changes during attestation.'}
                        </div>
                    ) : (
                        <div className="bg-white rounded-lg shadow overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change Type</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Attestation Model</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target/Details</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {filteredLinkedChanges.map((link) => (
                                        <tr key={link.link_id}>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                    link.change_type === 'MODEL_EDIT' ? 'bg-blue-100 text-blue-800' :
                                                    link.change_type === 'NEW_MODEL' ? 'bg-green-100 text-green-800' :
                                                    'bg-red-100 text-red-800'
                                                }`}>
                                                    {link.change_type === 'MODEL_EDIT' ? 'Model Edit' :
                                                     link.change_type === 'NEW_MODEL' ? 'New Model' :
                                                     'Decommission'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {link.attestation?.model && (
                                                    <Link
                                                        to={`/attestations/${link.attestation_id}`}
                                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                                    >
                                                        {link.attestation.model.model_name}
                                                    </Link>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {link.attestation?.owner?.full_name || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {link.attestation?.cycle?.cycle_name || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {link.change_type === 'NEW_MODEL' && link.model && (
                                                    <Link
                                                        to={`/models/${link.model.model_id}`}
                                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                                    >
                                                        {link.model.model_name}
                                                    </Link>
                                                )}
                                                {link.change_type === 'MODEL_EDIT' && link.pending_edit_id && (
                                                    <span className="text-gray-600">
                                                        Edit #{link.pending_edit_id}
                                                        {link.model && (
                                                            <>
                                                                {' for '}
                                                                <Link
                                                                    to={`/models/${link.model.model_id}`}
                                                                    className="text-blue-600 hover:text-blue-800 hover:underline"
                                                                >
                                                                    {link.model.model_name}
                                                                </Link>
                                                            </>
                                                        )}
                                                    </span>
                                                )}
                                                {link.change_type === 'DECOMMISSION' && link.decommissioning_request_id && (
                                                    <Link
                                                        to={`/models/${link.model_id}/decommission`}
                                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                                    >
                                                        Request #{link.decommissioning_request_id}
                                                    </Link>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {link.pending_edit?.status && (
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        link.pending_edit.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                                                        link.pending_edit.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                        {link.pending_edit.status}
                                                    </span>
                                                )}
                                                {link.decommissioning_request?.status && (
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        link.decommissioning_request.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                                                        link.decommissioning_request.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                        {link.decommissioning_request.status}
                                                    </span>
                                                )}
                                                {link.change_type === 'NEW_MODEL' && !link.pending_edit && !link.decommissioning_request && (
                                                    <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                        Created
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {link.created_at ? link.created_at.split('T')[0] : '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                <Link
                                                    to={`/attestations/${link.attestation_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    View Attestation
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Force Close Confirmation Modal */}
            {showForceCloseModal && (
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
                        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={cancelForceClose}></div>
                        <div className="relative inline-block w-full max-w-lg px-4 pt-5 pb-4 overflow-hidden text-left align-bottom transition-all transform bg-white rounded-lg shadow-xl sm:my-8 sm:align-middle sm:p-6">
                            <div className="sm:flex sm:items-start">
                                <div className="flex items-center justify-center flex-shrink-0 w-12 h-12 mx-auto bg-red-100 rounded-full sm:mx-0 sm:h-10 sm:w-10">
                                    <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                </div>
                                <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                                    <h3 className="text-lg font-medium leading-6 text-gray-900">
                                        Force Close Cycle
                                    </h3>
                                    <div className="mt-2">
                                        <p className="text-sm text-gray-500">
                                            This cycle has unmet coverage targets. Force closing will bypass these requirements.
                                        </p>

                                        {forceCloseBlockingGaps.length > 0 && (
                                            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                                                <p className="text-sm font-medium text-red-800 mb-2">Blocking Gaps:</p>
                                                <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                                                    {forceCloseBlockingGaps.map((gap, index) => (
                                                        <li key={index}>{gap}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        <div className="mt-4">
                                            <label className="block text-sm font-medium text-gray-700">
                                                Reason for Force Close <span className="text-red-600">*</span>
                                            </label>
                                            <textarea
                                                value={forceCloseReason}
                                                onChange={(e) => setForceCloseReason(e.target.value)}
                                                rows={3}
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500 sm:text-sm"
                                                placeholder="Provide justification for overriding coverage targets..."
                                                required
                                            />
                                            <p className="mt-1 text-xs text-gray-500">
                                                This reason will be recorded in the audit trail.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse gap-3">
                                <button
                                    type="button"
                                    onClick={handleForceCloseCycle}
                                    disabled={!forceCloseReason.trim()}
                                    className="inline-flex justify-center w-full px-4 py-2 text-base font-medium text-white bg-red-600 border border-transparent rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Force Close
                                </button>
                                <button
                                    type="button"
                                    onClick={cancelForceClose}
                                    className="inline-flex justify-center w-full px-4 py-2 mt-3 text-base font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:w-auto sm:text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

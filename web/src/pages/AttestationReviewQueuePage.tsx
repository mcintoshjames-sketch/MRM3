import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

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

interface DashboardStats {
    pending_count: number;
    submitted_count: number;
    overdue_count: number;
    pending_changes: number;
    active_cycles: number;
}

type FilterCycle = 'all' | number;

export default function AttestationReviewQueuePage() {
    const [records, setRecords] = useState<AttestationRecord[]>([]);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterCycle, setFilterCycle] = useState<FilterCycle>('all');
    const [cycles, setCycles] = useState<{ cycle_id: number; cycle_name: string }[]>([]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [recordsRes, statsRes, cyclesRes] = await Promise.all([
                api.get('/attestations/records?status=SUBMITTED'),
                api.get('/attestations/dashboard/stats'),
                api.get('/attestations/cycles?status=OPEN')
            ]);
            setRecords(recordsRes.data);
            setStats(statsRes.data);
            setCycles(cyclesRes.data.map((c: any) => ({ cycle_id: c.cycle_id, cycle_name: c.cycle_name })));
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load review queue');
        } finally {
            setLoading(false);
        }
    };

    const filteredRecords = records.filter(r => {
        if (filterCycle === 'all') return true;
        return r.cycle_id === filterCycle;
    });

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

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

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Attestation Review Queue</h1>
                <p className="text-gray-600 mt-1">Review and approve submitted attestations</p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">&times;</button>
                </div>
            )}

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
                        {cycles.map(c => (
                            <option key={c.cycle_id} value={c.cycle_id}>{c.cycle_name}</option>
                        ))}
                    </select>
                    <button
                        onClick={fetchData}
                        className="btn-secondary ml-auto"
                    >
                        Refresh
                    </button>
                </div>
            </div>

            {/* Review Queue Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">Loading...</div>
                ) : filteredRecords.length === 0 ? (
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
                            {filteredRecords.map((record) => (
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
        </Layout>
    );
}

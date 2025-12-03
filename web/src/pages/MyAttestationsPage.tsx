import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

// Interfaces
interface MyAttestation {
    attestation_id: number;
    cycle_id: number;
    cycle_name: string;
    model_id: number;
    model_name: string;
    model_risk_tier: string;
    due_date: string;
    status: 'PENDING' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';
    attested_at: string | null;
    decision: string | null;
    rejection_reason: string | null;
    days_until_due: number;
}

interface UpcomingWidget {
    current_cycle: {
        cycle_id: number;
        cycle_name: string;
        submission_due_date: string;
        status: string;
    } | null;
    attestations: MyAttestation[];
    pending_count: number;
    overdue_count: number;
    days_until_due: number | null;
}

type FilterStatus = 'all' | 'PENDING' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';

export default function MyAttestationsPage() {
    const [attestations, setAttestations] = useState<MyAttestation[]>([]);
    const [loading, setLoading] = useState(true);
    const [upcomingData, setUpcomingData] = useState<UpcomingWidget | null>(null);
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [attestationsRes, upcomingRes] = await Promise.all([
                api.get('/attestations/my-attestations'),
                api.get('/attestations/my-upcoming')
            ]);
            setAttestations(attestationsRes.data);
            setUpcomingData(upcomingRes.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load attestations');
        } finally {
            setLoading(false);
        }
    };

    const filteredAttestations = attestations.filter(att => {
        if (filterStatus === 'all') return true;
        return att.status === filterStatus;
    });

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'SUBMITTED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">Submitted</span>;
            case 'ACCEPTED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Accepted</span>;
            case 'REJECTED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">Rejected</span>;
            default:
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">Pending</span>;
        }
    };

    const getUrgencyBadge = (daysUntilDue: number, status: string) => {
        if (status !== 'PENDING') return null;

        if (daysUntilDue < 0) {
            return <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-red-500 text-white">Overdue</span>;
        } else if (daysUntilDue <= 7) {
            return <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">Due Soon</span>;
        }
        return null;
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    const pendingCount = attestations.filter(a => a.status === 'PENDING').length;
    const overdueCount = attestations.filter(a => a.status === 'PENDING' && a.days_until_due < 0).length;
    const submittedCount = attestations.filter(a => a.status === 'SUBMITTED').length;
    const acceptedCount = attestations.filter(a => a.status === 'ACCEPTED').length;

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">My Attestations</h1>
                <p className="text-gray-600 mt-1">View and submit your model risk attestations</p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">&times;</button>
                </div>
            )}

            {/* Summary Cards */}
            {upcomingData && upcomingData.current_cycle && (
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 mb-6 text-white">
                    <div className="flex justify-between items-start">
                        <div>
                            <h2 className="text-lg font-semibold opacity-90">Current Cycle</h2>
                            <div className="text-2xl font-bold mt-1">{upcomingData.current_cycle.cycle_name}</div>
                            <div className="mt-2 opacity-80">
                                Due: {formatDate(upcomingData.current_cycle.submission_due_date)}
                                {upcomingData.days_until_due !== null && (
                                    <span className="ml-2">
                                        ({upcomingData.days_until_due < 0
                                            ? `${Math.abs(upcomingData.days_until_due)} days overdue`
                                            : `${upcomingData.days_until_due} days remaining`})
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-4xl font-bold">{upcomingData.pending_count}</div>
                            <div className="text-sm opacity-80">Pending</div>
                            {upcomingData.overdue_count > 0 && (
                                <div className="mt-2 px-3 py-1 bg-red-500 rounded-full text-sm font-medium">
                                    {upcomingData.overdue_count} Overdue
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div
                    className={`bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md ${
                        filterStatus === 'PENDING' ? 'ring-2 ring-yellow-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'PENDING' ? 'all' : 'PENDING')}
                >
                    <div className="text-sm text-gray-500">Pending</div>
                    <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
                </div>
                <div
                    className={`bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md ${
                        filterStatus === 'SUBMITTED' ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'SUBMITTED' ? 'all' : 'SUBMITTED')}
                >
                    <div className="text-sm text-gray-500">Submitted (Pending Review)</div>
                    <div className="text-2xl font-bold text-blue-600">{submittedCount}</div>
                </div>
                <div
                    className={`bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md ${
                        filterStatus === 'ACCEPTED' ? 'ring-2 ring-green-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'ACCEPTED' ? 'all' : 'ACCEPTED')}
                >
                    <div className="text-sm text-gray-500">Accepted</div>
                    <div className="text-2xl font-bold text-green-600">{acceptedCount}</div>
                </div>
                <div
                    className={`bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md ${
                        filterStatus === 'REJECTED' ? 'ring-2 ring-red-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'REJECTED' ? 'all' : 'REJECTED')}
                >
                    <div className="text-sm text-gray-500">Overdue</div>
                    <div className="text-2xl font-bold text-red-600">{overdueCount}</div>
                </div>
            </div>

            {/* Filter Status Indicator */}
            {filterStatus !== 'all' && (
                <div className="mb-4 flex items-center">
                    <span className="text-sm text-gray-600">
                        Showing: <strong>{filterStatus}</strong> attestations
                    </span>
                    <button
                        onClick={() => setFilterStatus('all')}
                        className="ml-2 text-blue-600 hover:text-blue-800 text-sm"
                    >
                        Clear filter
                    </button>
                </div>
            )}

            {/* Attestations Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">Loading...</div>
                ) : filteredAttestations.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        {filterStatus === 'all'
                            ? 'No attestations found. They will appear here when an attestation cycle is opened.'
                            : `No ${filterStatus.toLowerCase()} attestations found.`}
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredAttestations.map((att) => (
                                <tr key={att.attestation_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/models/${att.model_id}`}
                                            className="text-blue-600 hover:text-blue-800 font-medium"
                                        >
                                            {att.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {att.model_risk_tier}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {att.cycle_name}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <span className={att.days_until_due < 0 && att.status === 'PENDING' ? 'text-red-600 font-medium' : 'text-gray-500'}>
                                            {formatDate(att.due_date)}
                                        </span>
                                        {getUrgencyBadge(att.days_until_due, att.status)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {getStatusBadge(att.status)}
                                        {att.status === 'REJECTED' && att.rejection_reason && (
                                            <div className="text-xs text-red-600 mt-1 max-w-xs truncate" title={att.rejection_reason}>
                                                {att.rejection_reason}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {att.status === 'PENDING' && (
                                            <Link
                                                to={`/attestations/${att.attestation_id}`}
                                                className="btn-primary text-sm py-1 px-3"
                                            >
                                                Submit
                                            </Link>
                                        )}
                                        {att.status === 'REJECTED' && (
                                            <Link
                                                to={`/attestations/${att.attestation_id}`}
                                                className="btn-secondary text-sm py-1 px-3"
                                            >
                                                Resubmit
                                            </Link>
                                        )}
                                        {(att.status === 'SUBMITTED' || att.status === 'ACCEPTED') && (
                                            <Link
                                                to={`/attestations/${att.attestation_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View
                                            </Link>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Help Text */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-blue-800 mb-2">About Attestations</h3>
                <ul className="text-sm text-blue-700 space-y-1">
                    <li>• Attestations confirm your models comply with the Model Risk and Validation Policy</li>
                    <li>• Each attestation requires you to answer a series of compliance questions</li>
                    <li>• Submitted attestations are reviewed by the Model Validation team</li>
                    <li>• If rejected, you will need to address the concerns and resubmit</li>
                </ul>
            </div>
        </Layout>
    );
}

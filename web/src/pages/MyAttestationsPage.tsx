import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

// Interfaces
interface MyAttestation {
    attestation_id: number;
    cycle_id: number;
    cycle_name: string;
    model_id: number;
    model_name: string;
    model_risk_tier: string | null;
    risk_tier_code: string | null;
    due_date: string;
    status: 'PENDING' | 'SUBMITTED' | 'ADMIN_REVIEW' | 'ACCEPTED' | 'REJECTED';
    attested_at: string | null;
    decision: string | null;
    rejection_reason: string | null;
    days_until_due: number;
    is_overdue: boolean;
    can_submit: boolean;
    is_excluded: boolean;
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

type FilterStatus = 'all' | 'PENDING' | 'SUBMITTED' | 'ADMIN_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'INDIVIDUAL' | 'OVERDUE';

export default function MyAttestationsPage() {
    const navigate = useNavigate();
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

    // Filter logic based on selected filter
    const filteredAttestations = attestations.filter(att => {
        if (filterStatus === 'all') return true;
        if (filterStatus === 'INDIVIDUAL') {
            // Show excluded pending or rejected models that need individual attention
            return (att.status === 'PENDING' && att.is_excluded) || att.status === 'REJECTED';
        }
        if (filterStatus === 'OVERDUE') {
            return att.status === 'PENDING' && att.days_until_due < 0;
        }
        return att.status === filterStatus;
    });

    const getStatusBadge = (status: string, isExcluded: boolean = false) => {
        if (status === 'PENDING' && isExcluded) {
            return (
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">
                    Individual Required
                </span>
            );
        }
        switch (status) {
            case 'SUBMITTED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">Submitted</span>;
            case 'ADMIN_REVIEW':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">Admin Review</span>;
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

    // Count categories
    const pendingCount = attestations.filter(a => a.status === 'PENDING').length;
    const pendingBulkCount = attestations.filter(a => a.status === 'PENDING' && !a.is_excluded).length;
    const pendingIndividualCount = attestations.filter(a => a.status === 'PENDING' && a.is_excluded).length;
    const overdueCount = attestations.filter(a => a.status === 'PENDING' && a.days_until_due < 0).length;
    const submittedCount = attestations.filter(a => a.status === 'SUBMITTED').length;
    const acceptedCount = attestations.filter(a => a.status === 'ACCEPTED').length;
    const rejectedCount = attestations.filter(a => a.status === 'REJECTED').length;
    const individualRequiredCount = pendingIndividualCount + rejectedCount;

    const hasActiveFilter = filterStatus !== 'all';
    const filterLabel = filterStatus === 'INDIVIDUAL'
        ? 'Individual Required'
        : filterStatus === 'OVERDUE'
        ? 'Overdue'
        : filterStatus;

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

            {/* Current Cycle Header */}
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
                            {/* Bulk Attestation CTA - show when 2+ non-excluded pending models */}
                            {pendingBulkCount >= 2 && (
                                <button
                                    onClick={() => navigate(`/attestations/bulk/${upcomingData.current_cycle!.cycle_id}`)}
                                    className="mt-4 bg-white text-blue-600 hover:bg-blue-50 font-semibold py-2 px-4 rounded-lg shadow-sm transition-colors"
                                >
                                    Bulk Attest ({pendingBulkCount} models)
                                </button>
                            )}
                        </div>
                        <div className="text-right">
                            <div className="text-4xl font-bold">{pendingCount}</div>
                            <div className="text-sm opacity-80">Pending</div>
                            {overdueCount > 0 && (
                                <div className="mt-2 px-3 py-1 bg-red-500 rounded-full text-sm font-medium">
                                    {overdueCount} Overdue
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Individual Attestation Required Alert */}
            {individualRequiredCount > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
                    <div className="flex items-start gap-3">
                        <div className="text-orange-500 text-xl">⚠️</div>
                        <div className="flex-1">
                            <h3 className="text-sm font-semibold text-orange-800">
                                {individualRequiredCount} Model{individualRequiredCount > 1 ? 's' : ''} Require Individual Attention
                            </h3>
                            <p className="text-sm text-orange-700 mt-1">
                                {pendingIndividualCount > 0 && (
                                    <span>{pendingIndividualCount} excluded from bulk attestation</span>
                                )}
                                {pendingIndividualCount > 0 && rejectedCount > 0 && <span>, </span>}
                                {rejectedCount > 0 && (
                                    <span>{rejectedCount} rejected and need resubmission</span>
                                )}
                            </p>
                            <button
                                onClick={() => setFilterStatus('INDIVIDUAL')}
                                className="mt-2 text-sm font-medium text-orange-700 hover:text-orange-900 underline"
                            >
                                Show individual attestations →
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <button
                    type="button"
                    aria-pressed={filterStatus === 'PENDING'}
                    className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 ${
                        filterStatus === 'PENDING' ? 'ring-2 ring-yellow-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'PENDING' ? 'all' : 'PENDING')}
                >
                    <div className="text-sm text-gray-500">Pending</div>
                    <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
                </button>
                <button
                    type="button"
                    aria-pressed={filterStatus === 'INDIVIDUAL'}
                    className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 ${
                        filterStatus === 'INDIVIDUAL' ? 'ring-2 ring-orange-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'INDIVIDUAL' ? 'all' : 'INDIVIDUAL')}
                >
                    <div className="text-sm text-gray-500">Individual Required</div>
                    <div className="text-2xl font-bold text-orange-600">{individualRequiredCount}</div>
                </button>
                <button
                    type="button"
                    aria-pressed={filterStatus === 'SUBMITTED'}
                    className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                        filterStatus === 'SUBMITTED' ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'SUBMITTED' ? 'all' : 'SUBMITTED')}
                >
                    <div className="text-sm text-gray-500">Submitted</div>
                    <div className="text-2xl font-bold text-blue-600">{submittedCount}</div>
                </button>
                <button
                    type="button"
                    aria-pressed={filterStatus === 'ACCEPTED'}
                    className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
                        filterStatus === 'ACCEPTED' ? 'ring-2 ring-green-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'ACCEPTED' ? 'all' : 'ACCEPTED')}
                >
                    <div className="text-sm text-gray-500">Accepted</div>
                    <div className="text-2xl font-bold text-green-600">{acceptedCount}</div>
                </button>
                <button
                    type="button"
                    aria-pressed={filterStatus === 'OVERDUE'}
                    className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                        filterStatus === 'OVERDUE' ? 'ring-2 ring-red-500' : ''
                    }`}
                    onClick={() => setFilterStatus(filterStatus === 'OVERDUE' ? 'all' : 'OVERDUE')}
                >
                    <div className="text-sm text-gray-500">Overdue</div>
                    <div className="text-2xl font-bold text-red-600">{overdueCount}</div>
                </button>
            </div>

            {/* Filter Status Indicator */}
            {hasActiveFilter && (
                <div className="mb-4 flex flex-wrap items-center gap-3">
                    <span className="text-sm text-gray-600">
                        Showing: <strong>{filterLabel}</strong> attestations
                    </span>
                    <button
                        onClick={() => setFilterStatus('all')}
                        className="btn-secondary text-sm"
                    >
                        Clear filters
                    </button>
                </div>
            )}

            {/* Register New Model Button */}
            <div className="mb-4 flex justify-end">
                <button
                    onClick={() => navigate('/models?create=true')}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Register New Model
                </button>
            </div>

            {/* Attestations Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">Loading...</div>
                ) : filteredAttestations.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        {filterStatus === 'all'
                            ? 'No attestations found. They will appear here when an attestation cycle is opened.'
                            : filterStatus === 'INDIVIDUAL'
                            ? 'No individual attestations required at this time.'
                            : `No ${filterStatus.toLowerCase()} attestations found.`}
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Cycle</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredAttestations.map((att) => (
                                <tr
                                    key={att.attestation_id}
                                    className={`hover:bg-gray-50 ${
                                        att.status === 'PENDING' && att.is_excluded ? 'bg-orange-50' : ''
                                    }`}
                                >
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <Link
                                            to={`/models/${att.model_id}`}
                                            className="text-blue-600 hover:text-blue-800 font-medium"
                                        >
                                            {att.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                        {att.model_risk_tier || att.risk_tier_code || '-'}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                        {att.cycle_name}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                        <span className={att.days_until_due < 0 && att.status === 'PENDING' ? 'text-red-600 font-medium' : 'text-gray-500'}>
                                            {formatDate(att.due_date)}
                                        </span>
                                        {getUrgencyBadge(att.days_until_due, att.status)}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        {getStatusBadge(att.status, att.is_excluded)}
                                        {att.status === 'REJECTED' && att.rejection_reason && (
                                            <div className="text-xs text-red-600 mt-1 max-w-xs truncate" title={att.rejection_reason}>
                                                {att.rejection_reason}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
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
                    <li>• <strong>Bulk attestation</strong> lets you attest multiple similar models at once</li>
                    <li>• <strong>Individual attestation</strong> is required for models excluded from bulk or that need specific attention</li>
                    <li>• Submitted attestations are reviewed by the Model Validation team</li>
                    <li>• If rejected, you will need to address the concerns and resubmit</li>
                </ul>
            </div>
        </Layout>
    );
}

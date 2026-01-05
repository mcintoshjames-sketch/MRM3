import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { irpApi, IRPDetail, IRPReviewCreate, IRPCertificationCreate } from '../api/irp';
import api from '../api/client';
import { canManageIrps } from '../utils/roleUtils';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
}

type TabType = 'overview' | 'mrsas' | 'reviews' | 'certifications';

export default function IRPDetailPage() {
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();
    const canManageIrpsFlag = canManageIrps(user);

    const [irp, setIrp] = useState<IRPDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [outcomeOptions, setOutcomeOptions] = useState<TaxonomyValue[]>([]);

    // Review form state
    const [showReviewForm, setShowReviewForm] = useState(false);
    const [reviewForm, setReviewForm] = useState<IRPReviewCreate>({
        review_date: new Date().toISOString().split('T')[0],
        outcome_id: 0,
        notes: ''
    });

    // Certification form state
    const [showCertForm, setShowCertForm] = useState(false);
    const [certForm, setCertForm] = useState<IRPCertificationCreate>({
        certification_date: new Date().toISOString().split('T')[0],
        conclusion_summary: ''
    });

    useEffect(() => {
        fetchData();
    }, [id, canManageIrpsFlag]);

    const fetchData = async () => {
        if (!id) return;
        setLoading(true);
        try {
            const irpData = await irpApi.get(parseInt(id));
            setIrp(irpData);

            if (canManageIrpsFlag) {
                const taxonomiesResponse = await api.get('/taxonomies/by-names/?names=IRP%20Review%20Outcome');
                const outcomeTaxonomy = taxonomiesResponse.data.find(
                    (t: any) => t.name === 'IRP Review Outcome'
                );
                if (outcomeTaxonomy && outcomeTaxonomy.values) {
                    setOutcomeOptions(outcomeTaxonomy.values.filter((v: TaxonomyValue) => v.code));
                }
            } else {
                setOutcomeOptions([]);
            }
        } catch (error) {
            console.error('Failed to fetch IRP:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateReview = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!id || !reviewForm.outcome_id) {
            alert('Please select an outcome');
            return;
        }
        try {
            await irpApi.createReview(parseInt(id), reviewForm);
            setShowReviewForm(false);
            setReviewForm({
                review_date: new Date().toISOString().split('T')[0],
                outcome_id: 0,
                notes: ''
            });
            fetchData();
        } catch (error: any) {
            console.error('Failed to create review:', error);
            alert(error.response?.data?.detail || 'Failed to create review');
        }
    };

    const handleCreateCertification = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!id || !certForm.conclusion_summary.trim()) {
            alert('Please provide a conclusion summary');
            return;
        }
        try {
            await irpApi.createCertification(parseInt(id), certForm);
            setShowCertForm(false);
            setCertForm({
                certification_date: new Date().toISOString().split('T')[0],
                conclusion_summary: ''
            });
            fetchData();
        } catch (error: any) {
            console.error('Failed to create certification:', error);
            alert(error.response?.data?.detail || 'Failed to create certification');
        }
    };

    const getOutcomeColor = (code: string) => {
        switch (code) {
            case 'SATISFACTORY':
                return 'bg-green-100 text-green-800';
            case 'CONDITIONALLY_SATISFACTORY':
                return 'bg-yellow-100 text-yellow-800';
            case 'NOT_SATISFACTORY':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-700';
        }
    };

    const backLink = canManageIrpsFlag ? '/irps' : '/my-mrsa-reviews';
    const backLabel = canManageIrpsFlag ? 'IRPs' : 'My MRSA Reviews';

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">Loading...</div>
            </Layout>
        );
    }

    if (!irp) {
        return (
            <Layout>
                <div className="p-6">
                    <div className="text-center py-12">
                        <h2 className="text-xl font-semibold text-gray-700">IRP not found</h2>
                        <Link to={backLink} className="text-blue-600 hover:underline mt-2 inline-block">
                            Back to {backLabel}
                        </Link>
                    </div>
                </div>
            </Layout>
        );
    }

    const tabs: { key: TabType; label: string; count?: number }[] = [
        { key: 'overview', label: 'Overview' },
        { key: 'mrsas', label: 'Covered MRSAs', count: irp.covered_mrsa_count },
        { key: 'reviews', label: 'Reviews', count: irp.reviews?.length || 0 },
        { key: 'certifications', label: 'Certifications', count: irp.certifications?.length || 0 }
    ];

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6">
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                        <Link to={backLink} className="hover:text-blue-600">{backLabel}</Link>
                        <span>/</span>
                        <span>{irp.process_name}</span>
                    </div>
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                                {irp.process_name}
                                <span className={`px-2 py-1 text-sm rounded font-medium ${
                                    irp.is_active
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-gray-100 text-gray-700'
                                }`}>
                                    {irp.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </h1>
                            <p className="text-gray-600 mt-1">
                                Contact: {irp.contact_user?.full_name || 'Unknown'}
                            </p>
                        </div>
                        <Link to={backLink} className="btn-secondary">
                            ← Back to {backLabel}
                        </Link>
                    </div>
                </div>

                {/* Tabs */}
                <div className="border-b border-gray-200 mb-6">
                    <nav className="-mb-px flex space-x-8">
                        {tabs.map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                                    activeTab === tab.key
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                {tab.label}
                                {tab.count !== undefined && (
                                    <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                                        activeTab === tab.key
                                            ? 'bg-blue-100 text-blue-600'
                                            : 'bg-gray-100 text-gray-600'
                                    }`}>
                                        {tab.count}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Tab Content */}
                <div className="bg-white rounded-lg shadow-md">
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div className="p-6">
                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Process Name</h3>
                                    <p className="text-gray-900">{irp.process_name}</p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Contact</h3>
                                    <p className="text-gray-900">
                                        {irp.contact_user ? (
                                            <Link
                                                to={`/users/${irp.contact_user_id}`}
                                                className="text-blue-600 hover:underline"
                                            >
                                                {irp.contact_user.full_name}
                                            </Link>
                                        ) : (
                                            'Unknown'
                                        )}
                                    </p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
                                    <span className={`px-2 py-1 text-sm rounded font-medium ${
                                        irp.is_active
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-gray-100 text-gray-700'
                                    }`}>
                                        {irp.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Covered MRSAs</h3>
                                    <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-sm font-medium">
                                        {irp.covered_mrsa_count}
                                    </span>
                                </div>
                                <div className="col-span-2">
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Description</h3>
                                    <p className="text-gray-900">{irp.description || 'No description provided'}</p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Latest Review</h3>
                                    {irp.latest_review ? (
                                        <div>
                                            <span className="text-gray-900">{irp.latest_review.review_date}</span>
                                            {irp.latest_review.outcome && (
                                                <span className={`ml-2 px-2 py-0.5 text-xs rounded ${
                                                    getOutcomeColor(irp.latest_review.outcome.code)
                                                }`}>
                                                    {irp.latest_review.outcome.label}
                                                </span>
                                            )}
                                        </div>
                                    ) : (
                                        <span className="text-gray-400">No reviews yet</span>
                                    )}
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Latest Certification</h3>
                                    {irp.latest_certification ? (
                                        <span className="text-gray-900">{irp.latest_certification.certification_date}</span>
                                    ) : (
                                        <span className="text-gray-400">Not certified</span>
                                    )}
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Created</h3>
                                    <p className="text-gray-900">{irp.created_at.split('T')[0]}</p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Last Updated</h3>
                                    <p className="text-gray-900">{irp.updated_at.split('T')[0]}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* MRSAs Tab */}
                    {activeTab === 'mrsas' && (
                        <div className="p-6">
                            {irp.covered_mrsas.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">
                                    No MRSAs are covered by this IRP.
                                </p>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                MRSA Name
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Risk Level
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Owner
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {irp.covered_mrsas.map((mrsa) => (
                                            <tr key={mrsa.model_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 whitespace-nowrap">
                                                    <Link
                                                        to={`/models/${mrsa.model_id}`}
                                                        className="text-blue-600 hover:underline font-medium"
                                                    >
                                                        {mrsa.model_name}
                                                    </Link>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap">
                                                    {mrsa.mrsa_risk_level_label ? (
                                                        <span className={`px-2 py-1 text-xs rounded font-medium ${
                                                            mrsa.mrsa_risk_level_label === 'High-Risk'
                                                                ? 'bg-red-100 text-red-800'
                                                                : 'bg-green-100 text-green-800'
                                                        }`}>
                                                            {mrsa.mrsa_risk_level_label}
                                                        </span>
                                                    ) : (
                                                        <span className="text-gray-400">-</span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                                    {mrsa.owner_name || '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}

                    {/* Reviews Tab */}
                    {activeTab === 'reviews' && (
                        <div className="p-6">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-semibold">Review History</h3>
                                {canManageIrpsFlag && (
                                    <button
                                        onClick={() => setShowReviewForm(true)}
                                        className="btn-primary"
                                    >
                                        + Add Review
                                    </button>
                                )}
                            </div>

                            {/* Review Form */}
                            {showReviewForm && canManageIrpsFlag && (
                                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                    <h4 className="font-medium mb-3">New Review</h4>
                                    <form onSubmit={handleCreateReview}>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium mb-1">
                                                    Review Date *
                                                </label>
                                                <input
                                                    type="date"
                                                    className="input-field"
                                                    value={reviewForm.review_date}
                                                    onChange={(e) => setReviewForm({
                                                        ...reviewForm,
                                                        review_date: e.target.value
                                                    })}
                                                    required
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-1">
                                                    Outcome *
                                                </label>
                                                <select
                                                    className="input-field"
                                                    value={reviewForm.outcome_id}
                                                    onChange={(e) => setReviewForm({
                                                        ...reviewForm,
                                                        outcome_id: parseInt(e.target.value)
                                                    })}
                                                    required
                                                >
                                                    <option value={0}>Select outcome...</option>
                                                    {outcomeOptions.map((opt) => (
                                                        <option key={opt.value_id} value={opt.value_id}>
                                                            {opt.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-sm font-medium mb-1">
                                                    Notes
                                                </label>
                                                <textarea
                                                    className="input-field"
                                                    rows={3}
                                                    value={reviewForm.notes}
                                                    onChange={(e) => setReviewForm({
                                                        ...reviewForm,
                                                        notes: e.target.value
                                                    })}
                                                    placeholder="Optional notes about the review..."
                                                />
                                            </div>
                                        </div>
                                        <div className="flex gap-2 mt-4">
                                            <button type="submit" className="btn-primary">
                                                Save Review
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setShowReviewForm(false)}
                                                className="btn-secondary"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            )}

                            {/* Reviews Table */}
                            {irp.reviews.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">
                                    No reviews recorded for this IRP.
                                </p>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Date
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Outcome
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Reviewed By
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Notes
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {irp.reviews
                                            .sort((a, b) => new Date(b.review_date).getTime() - new Date(a.review_date).getTime())
                                            .map((review) => (
                                                <tr key={review.review_id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                        {review.review_date}
                                                    </td>
                                                    <td className="px-4 py-2 whitespace-nowrap">
                                                        {review.outcome && (
                                                            <span className={`px-2 py-1 text-xs rounded font-medium ${
                                                                getOutcomeColor(review.outcome.code)
                                                            }`}>
                                                                {review.outcome.label}
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                                        {review.reviewed_by?.full_name || '-'}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-gray-500 max-w-xs truncate">
                                                        {review.notes || '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}

                    {/* Certifications Tab */}
                    {activeTab === 'certifications' && (
                        <div className="p-6">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-semibold">Certification History</h3>
                                {canManageIrpsFlag && (
                                    <button
                                        onClick={() => setShowCertForm(true)}
                                        className="btn-primary"
                                    >
                                        + Add Certification
                                    </button>
                                )}
                            </div>

                            {/* Certification Form (Admin only) */}
                            {showCertForm && canManageIrpsFlag && (
                                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                    <h4 className="font-medium mb-3">New Certification</h4>
                                    <form onSubmit={handleCreateCertification}>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium mb-1">
                                                    Certification Date *
                                                </label>
                                                <input
                                                    type="date"
                                                    className="input-field"
                                                    value={certForm.certification_date}
                                                    onChange={(e) => setCertForm({
                                                        ...certForm,
                                                        certification_date: e.target.value
                                                    })}
                                                    required
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-sm font-medium mb-1">
                                                    Conclusion Summary *
                                                </label>
                                                <textarea
                                                    className="input-field"
                                                    rows={3}
                                                    value={certForm.conclusion_summary}
                                                    onChange={(e) => setCertForm({
                                                        ...certForm,
                                                        conclusion_summary: e.target.value
                                                    })}
                                                    placeholder="Summary of IRP design adequacy assessment..."
                                                    required
                                                />
                                            </div>
                                        </div>
                                        <div className="flex gap-2 mt-4">
                                            <button type="submit" className="btn-primary">
                                                Save Certification
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setShowCertForm(false)}
                                                className="btn-secondary"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            )}

                            {/* Certifications Table */}
                            {irp.certifications.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">
                                    No certifications recorded for this IRP.
                                </p>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Date
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Certified By
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Conclusion Summary
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {irp.certifications
                                            .sort((a, b) => new Date(b.certification_date).getTime() - new Date(a.certification_date).getTime())
                                            .map((cert) => (
                                                <tr key={cert.certification_id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                        {cert.certification_date}
                                                    </td>
                                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                                        {cert.certified_by?.full_name || '-'}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-gray-500">
                                                        {cert.conclusion_summary}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
}

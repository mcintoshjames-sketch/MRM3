import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { canViewAdminDashboard } from '../utils/roleUtils';

interface PendingSubmission {
    request_id: number;
    model_id: number;
    model_name: string;
    validation_type: string;
    priority: string;
    request_date: string;
    submission_due_date: string | null;
    grace_period_end: string | null;
    model_validation_due_date: string | null;
    days_until_submission_due: number | null;
    days_until_validation_due: number | null;
    submission_status: string;
    model_compliance_status: string;
    urgency: string;
}

export default function MyPendingSubmissionsPage() {
    const { user } = useAuth();
    const canViewAdminDashboardFlag = canViewAdminDashboard(user);
    const [submissions, setSubmissions] = useState<PendingSubmission[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'overdue' | 'in_grace_period' | 'due_soon' | 'upcoming'>('all');

    useEffect(() => {
        fetchSubmissions();
    }, []);

    const fetchSubmissions = async () => {
        try {
            const response = await api.get('/validation-workflow/my-pending-submissions');
            setSubmissions(response.data);
        } catch (error) {
            console.error('Failed to fetch pending submissions:', error);
        } finally {
            setLoading(false);
        }
    };

    const getUrgencyBadge = (urgency: string) => {
        switch (urgency) {
            case 'overdue':
                return 'bg-red-100 text-red-800';
            case 'in_grace_period':
                return 'bg-orange-100 text-orange-800';
            case 'due_soon':
                return 'bg-yellow-100 text-yellow-800';
            default:
                return 'bg-blue-100 text-blue-800';
        }
    };

    const getUrgencyLabel = (urgency: string) => {
        switch (urgency) {
            case 'overdue':
                return 'Overdue';
            case 'in_grace_period':
                return 'In Grace Period';
            case 'due_soon':
                return 'Due Soon (< 30 days)';
            default:
                return 'Upcoming';
        }
    };

    const getFilteredSubmissions = () => {
        if (filter === 'all') {
            return submissions;
        }
        return submissions.filter(s => s.urgency === filter);
    };

    const filteredSubmissions = getFilteredSubmissions();

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">
                    <div className="text-gray-500">Loading...</div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">Pending Submissions</h1>
                <p className="mt-2 text-gray-600">
                    Revalidation documentation submissions needed for models
                </p>
                <p className="mt-1 text-sm text-gray-500">
                    Showing submissions that are overdue or due within the next 90 days
                </p>
            </div>

            {/* Filter buttons */}
            <div className="flex gap-2 mb-6">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    All ({submissions.length})
                </button>
                <button
                    onClick={() => setFilter('overdue')}
                    className={`px-4 py-2 rounded ${filter === 'overdue' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Overdue ({submissions.filter(s => s.urgency === 'overdue').length})
                </button>
                <button
                    onClick={() => setFilter('in_grace_period')}
                    className={`px-4 py-2 rounded ${filter === 'in_grace_period' ? 'bg-orange-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    In Grace Period ({submissions.filter(s => s.urgency === 'in_grace_period').length})
                </button>
                <button
                    onClick={() => setFilter('due_soon')}
                    className={`px-4 py-2 rounded ${filter === 'due_soon' ? 'bg-yellow-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Due Soon ({submissions.filter(s => s.urgency === 'due_soon').length})
                </button>
                <button
                    onClick={() => setFilter('upcoming')}
                    className={`px-4 py-2 rounded ${filter === 'upcoming' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Upcoming ({submissions.filter(s => s.urgency === 'upcoming').length})
                </button>
            </div>

            {filteredSubmissions.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="mt-2 text-lg font-medium text-gray-900">
                        {filter === 'all' ? 'No Pending Submissions' : `No ${getUrgencyLabel(filter)} Submissions`}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                        {filter === 'all'
                            ? 'You don\'t have any revalidation submissions due at this time.'
                            : `You don't have any ${getUrgencyLabel(filter).toLowerCase()} submissions.`
                        }
                    </p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Urgency
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Model
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Validation Type
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Submission Due
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Grace Period End
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Validation Due
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredSubmissions.map((submission) => (
                                <tr key={submission.request_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyBadge(submission.urgency)}`}>
                                            {getUrgencyLabel(submission.urgency)}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2">
                                        <Link
                                            to={`/models/${submission.model_id}`}
                                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                        >
                                            {submission.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                            {submission.validation_type}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <div className="text-sm text-gray-900">{submission.submission_due_date}</div>
                                        {submission.days_until_submission_due !== null && (
                                            <div className={`text-xs font-medium ${
                                                submission.days_until_submission_due < 0 ? 'text-red-600' :
                                                submission.days_until_submission_due < 30 ? 'text-yellow-600' :
                                                'text-gray-500'
                                            }`}>
                                                {submission.days_until_submission_due < 0 ?
                                                    `${Math.abs(submission.days_until_submission_due)} days overdue` :
                                                    `${submission.days_until_submission_due} days left`
                                                }
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {submission.grace_period_end}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <div className="text-sm text-gray-900">{submission.model_validation_due_date}</div>
                                        {submission.days_until_validation_due !== null && (
                                            <div className={`text-xs font-medium ${
                                                submission.days_until_validation_due < 0 ? 'text-red-600' :
                                                submission.days_until_validation_due < 60 ? 'text-orange-600' :
                                                'text-gray-500'
                                            }`}>
                                                {submission.days_until_validation_due < 0 ?
                                                    `${Math.abs(submission.days_until_validation_due)} days overdue` :
                                                    `${submission.days_until_validation_due} days left`
                                                }
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <Link
                                            to={`/validation-workflow/${submission.request_id}`}
                                            className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                                        >
                                            View Request
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* Summary Footer */}
                    <div className="bg-gray-50 px-4 py-2 border-t border-gray-200">
                        <div className="text-sm text-gray-600">
                            {filter !== 'all' ? (
                                <>
                                    Showing <span className="font-medium">{filteredSubmissions.length}</span> of <span className="font-medium">{submissions.length}</span> total submission{submissions.length !== 1 ? 's' : ''}
                                </>
                            ) : (
                                <>
                                    <span className="font-medium">{submissions.length}</span> total submission{submissions.length !== 1 ? 's' : ''} •
                                    <span className="ml-2 font-medium text-red-600">
                                        {submissions.filter(s => s.urgency === 'overdue').length}
                                    </span> overdue •
                                    <span className="ml-2 font-medium text-orange-600">
                                        {submissions.filter(s => s.urgency === 'in_grace_period').length}
                                    </span> in grace period •
                                    <span className="ml-2 font-medium text-yellow-600">
                                        {submissions.filter(s => s.urgency === 'due_soon').length}
                                    </span> due soon
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Help Text */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex">
                    <svg className="h-5 w-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div className="text-sm text-blue-800">
                        <p className="font-medium">About Revalidation Submissions</p>
                        <p className="mt-1">
                            {canViewAdminDashboardFlag ? (
                                <>
                                    This page shows all pending revalidation submissions across the organization.
                                    Model owners are responsible for submitting documentation when a revalidation is due.
                                    A 3-month grace period is provided after the submission due date. The validation must be completed
                                    before the "Validation Due" date to maintain compliance.
                                </>
                            ) : (
                                <>
                                    As a model owner, you're responsible for submitting documentation when a revalidation is due.
                                    You have a 3-month grace period after the submission due date. The validation must be completed
                                    before the "Validation Due" date to maintain compliance.
                                </>
                            )}
                        </p>
                        <p className="mt-2 text-xs text-blue-700">
                            <strong>Note:</strong> This page only shows submissions that are overdue or due within the next 90 days.
                            Submissions due further in the future are not displayed.
                        </p>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface NewsFeedItem {
    id: number;
    type: string;
    action: string | null;
    text: string;
    user_name: string;
    model_name: string;
    model_id: number;
    created_at: string;
}

interface MySubmission {
    model_id: number;
    model_name: string;
    description: string | null;
    development_type: string;
    owner: { full_name: string };
    submitted_at: string;
    row_approval_status: string;
}

export default function ModelOwnerDashboardPage() {
    const { user } = useAuth();
    const [newsFeed, setNewsFeed] = useState<NewsFeedItem[]>([]);
    const [mySubmissions, setMySubmissions] = useState<MySubmission[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [feedRes, submissionsRes] = await Promise.all([
                api.get('/dashboard/news-feed'),
                api.get('/models/my-submissions')
            ]);
            setNewsFeed(feedRes.data);
            setMySubmissions(submissionsRes.data);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatTimeAgo = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        return `${Math.floor(diffDays / 30)} months ago`;
    };

    const getActionIcon = (action: string | null) => {
        switch (action) {
            case 'approved':
                return (
                    <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                );
            case 'sent_back':
                return (
                    <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                );
            case 'submitted':
            case 'resubmitted':
                return (
                    <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                    </svg>
                );
        }
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
            <div className="mb-6">
                <h2 className="text-2xl font-bold">My Dashboard</h2>
                <p className="text-gray-600 mt-1">Welcome back, {user?.full_name}</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">My Records</h3>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{mySubmissions.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Pending approval</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Needs Revision</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                        {mySubmissions.filter(s => s.row_approval_status === 'needs_revision').length}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">Requires your attention</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Quick Actions</h3>
                    <div className="mt-2 space-y-1">
                        <Link to="/models" className="block text-blue-600 hover:text-blue-800 text-xs">
                            View My Models &rarr;
                        </Link>
                        <Link to="/models" className="block text-blue-600 hover:text-blue-800 text-xs">
                            Create New Model &rarr;
                        </Link>
                    </div>
                </div>
            </div>

            {/* My Pending Records */}
            {mySubmissions.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">My Model Records</h3>
                        <span className="text-xs text-gray-500 ml-auto">{mySubmissions.length} pending</span>
                    </div>
                    <div className="space-y-2">
                        {mySubmissions.map((submission) => (
                            <div
                                key={submission.model_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: submission.row_approval_status === 'needs_revision' ? '#f59e0b' : '#3b82f6'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                submission.row_approval_status === 'needs_revision'
                                                    ? 'bg-orange-100 text-orange-700'
                                                    : submission.row_approval_status === 'pending'
                                                    ? 'bg-blue-100 text-blue-700'
                                                    : 'bg-gray-100 text-gray-700'
                                            }`}>
                                                {submission.row_approval_status === 'needs_revision' ? 'Needs Revision' :
                                                 submission.row_approval_status === 'pending' ? 'Under Review' :
                                                 submission.row_approval_status}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                Submitted {formatTimeAgo(submission.submitted_at)}
                                            </span>
                                        </div>
                                        <Link
                                            to={`/models/${submission.model_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {submission.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            Owner: {submission.owner.full_name} • {submission.development_type}
                                        </p>
                                    </div>
                                    <div className="flex-shrink-0">
                                        {submission.row_approval_status === 'needs_revision' ? (
                                            <Link
                                                to={`/models/${submission.model_id}?edit=true`}
                                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-orange-600 hover:bg-orange-700 rounded transition-colors"
                                            >
                                                Edit & Resubmit
                                            </Link>
                                        ) : (
                                            <Link
                                                to={`/models/${submission.model_id}`}
                                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 border border-blue-600 hover:border-blue-800 rounded transition-colors"
                                            >
                                                View
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Activity News Feed */}
            <div className="bg-white p-4 rounded-lg shadow">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                    <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                        <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-700">Recent Activity</h3>
                    <span className="text-xs text-gray-500 ml-auto">{newsFeed.length} activities</span>
                </div>
                {newsFeed.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No recent activity on your models.</p>
                ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {newsFeed.map((item) => (
                            <div
                                key={item.id}
                                className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded"
                            >
                                {getActionIcon(item.action)}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-gray-800">
                                        <span className="font-medium">{item.user_name}</span>
                                        {item.action && (
                                            <span className="text-gray-600">
                                                {' '}{item.action === 'approved' ? 'approved' :
                                                      item.action === 'sent_back' ? 'sent back' :
                                                      item.action === 'submitted' ? 'submitted' :
                                                      item.action === 'resubmitted' ? 'resubmitted' :
                                                      'commented on'}
                                            </span>
                                        )}
                                        {' '}
                                        <Link to={`/models/${item.model_id}`} className="font-medium text-blue-600 hover:text-blue-800">
                                            {item.model_name}
                                        </Link>
                                    </p>
                                    <p className="text-xs text-gray-600 mt-0.5">{item.text}</p>
                                    <p className="text-xs text-gray-400 mt-0.5">{formatTimeAgo(item.created_at)}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Layout>
    );
}

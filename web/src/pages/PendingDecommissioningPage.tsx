import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';

interface DecommissioningRequest {
  request_id: number;
  model_id: number;
  model_name: string;
  status: string;
  reason: string;
  last_production_date: string;
  created_at: string;
  created_by_name: string;
}

export default function PendingDecommissioningPage() {
  const { user } = useAuth();
  const [requests, setRequests] = useState<DecommissioningRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isValidatorOrAdmin = user?.role === 'Admin' || user?.role === 'Validator';

  useEffect(() => {
    const fetchPendingRequests = async () => {
      try {
        setLoading(true);
        // Use different endpoints based on user role
        const endpoint = isValidatorOrAdmin
          ? '/decommissioning/pending-validator-review'
          : '/decommissioning/my-pending-owner-reviews';
        const response = await api.get(endpoint);
        setRequests(response.data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load pending decommissioning requests');
      } finally {
        setLoading(false);
      }
    };

    fetchPendingRequests();
  }, [isValidatorOrAdmin]);

  const getDaysUntilProduction = (lastProductionDate: string) => {
    const today = new Date();
    const prodDate = new Date(lastProductionDate);
    const diffTime = prodDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getUrgencyBadge = (lastProductionDate: string) => {
    const days = getDaysUntilProduction(lastProductionDate);
    if (days < 0) {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">Overdue</span>;
    } else if (days <= 7) {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">Due Soon</span>;
    } else if (days <= 30) {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">Upcoming</span>;
    }
    return null;
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Pending Decommissioning</h1>
          <p className="mt-2 text-sm text-gray-600">
            {isValidatorOrAdmin
              ? 'Review and approve model decommissioning requests'
              : 'Model decommissioning requests requiring your approval as model owner'}
          </p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700">{error}</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No pending requests</h3>
            <p className="mt-2 text-sm text-gray-500">
              {isValidatorOrAdmin
                ? 'All decommissioning requests have been reviewed.'
                : 'No decommissioning requests require your approval.'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reason
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Production Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Requested By
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Requested On
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
                {requests.map((request) => (
                  <tr key={request.request_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/models/${request.model_id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {request.model_name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {request.reason}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-900">{request.last_production_date}</span>
                        {getUrgencyBadge(request.last_production_date)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {request.created_by_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {request.created_at.split('T')[0]}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">
                        {request.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <Link
                        to={`/models/${request.model_id}/decommission`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}

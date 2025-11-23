import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';

interface DeploymentTask {
  task_id: number;
  model_name: string;
  version_number: string;
  region_code: string | null;
  region_name: string | null;
  planned_production_date: string;
  actual_production_date: string | null;
  days_until_due: number;
  status: string;
  assigned_to_name: string;
  deployed_before_validation_approved: boolean;
  validation_status: string | null;
}

interface ConfirmModalData {
  task_id: number;
  model_name: string;
  version_number: string;
  validation_status: string | null;
}

const MyDeploymentTasksPage = () => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<DeploymentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'overdue' | 'due-soon' | 'upcoming'>('all');

  // Confirm modal state
  const [confirmModal, setConfirmModal] = useState<ConfirmModalData | null>(null);
  const [actualDate, setActualDate] = useState('');
  const [confirmNotes, setConfirmNotes] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [validationWarning, setValidationWarning] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await api.get('/deployment-tasks/my-tasks');
      setTasks(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load deployment tasks');
    } finally {
      setLoading(false);
    }
  };

  const openConfirmModal = (task: DeploymentTask) => {
    setConfirmModal({
      task_id: task.task_id,
      model_name: task.model_name,
      version_number: task.version_number,
      validation_status: task.validation_status
    });
    setActualDate(new Date().toISOString().split('T')[0]);
    setConfirmNotes('');
    setOverrideReason('');
    setValidationWarning(null);

    // Show validation warning if not approved
    if (task.validation_status && task.validation_status !== 'Approved') {
      setValidationWarning(`Validation status is currently "${task.validation_status}". Deploying before validation approval may violate model risk policy.`);
    }
  };

  const handleConfirm = async () => {
    if (!confirmModal) return;

    const requiresOverride = confirmModal.validation_status && confirmModal.validation_status !== 'Approved';
    if (requiresOverride && !overrideReason.trim()) {
      alert('Override reason is required when deploying before validation approval');
      return;
    }

    try {
      setConfirmLoading(true);
      await api.patch(`/deployment-tasks/${confirmModal.task_id}/confirm`, {
        actual_production_date: actualDate,
        confirmation_notes: confirmNotes || null,
        validation_override_reason: requiresOverride ? overrideReason : null
      });

      setConfirmModal(null);
      fetchTasks();
    } catch (err: any) {
      // Check for validation error
      if (err.response?.status === 400 && err.response?.data?.detail?.error === 'validation_not_approved') {
        setValidationWarning(err.response.data.detail.message);
      } else {
        alert(err.response?.data?.detail || 'Failed to confirm deployment');
      }
    } finally {
      setConfirmLoading(false);
    }
  };

  const getFilteredTasks = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return tasks.filter(task => {
      if (task.status !== 'PENDING') return false;

      const daysUntilDue = task.days_until_due;

      switch (filter) {
        case 'overdue':
          return daysUntilDue < 0;
        case 'due-soon':
          return daysUntilDue >= 0 && daysUntilDue <= 7;
        case 'upcoming':
          return daysUntilDue > 7;
        default:
          return true;
      }
    });
  };

  const getStatusBadge = (task: DeploymentTask) => {
    if (task.status === 'CONFIRMED') {
      return <span className="px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800">Confirmed</span>;
    }

    if (task.days_until_due < 0) {
      return <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">Overdue</span>;
    } else if (task.days_until_due <= 7) {
      return <span className="px-2 py-1 text-xs font-semibold rounded bg-yellow-100 text-yellow-800">Due Soon</span>;
    } else {
      return <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">Upcoming</span>;
    }
  };

  const filteredTasks = getFilteredTasks();

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Pending Deployments</h1>
          <p className="mt-2 text-sm text-gray-600">
            Confirm when model versions are deployed to production
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        {/* Filter buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            All Pending ({tasks.filter(t => t.status === 'PENDING').length})
          </button>
          <button
            onClick={() => setFilter('overdue')}
            className={`px-4 py-2 rounded ${filter === 'overdue' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Overdue ({tasks.filter(t => t.status === 'PENDING' && t.days_until_due < 0).length})
          </button>
          <button
            onClick={() => setFilter('due-soon')}
            className={`px-4 py-2 rounded ${filter === 'due-soon' ? 'bg-yellow-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Due Soon ({tasks.filter(t => t.status === 'PENDING' && t.days_until_due >= 0 && t.days_until_due <= 7).length})
          </button>
          <button
            onClick={() => setFilter('upcoming')}
            className={`px-4 py-2 rounded ${filter === 'upcoming' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Upcoming ({tasks.filter(t => t.status === 'PENDING' && t.days_until_due > 7).length})
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading deployment tasks...</p>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-lg font-medium text-gray-900">
              {filter === 'all' ? 'No Pending Deployment Tasks' : `No ${filter.replace('-', ' ')} Tasks`.replace(/\b\w/g, l => l.toUpperCase())}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {filter === 'all'
                ? 'You don\'t have any pending deployment confirmations at this time.'
                : `You don't have any ${filter.replace('-', ' ')} deployment tasks.`
              }
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Planned Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Until Due</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTasks.map(task => (
                  <tr key={task.task_id} className={task.days_until_due < 0 ? 'bg-red-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{task.model_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{task.version_number}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {task.region_code ? `${task.region_name} (${task.region_code})` : 'Global'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {task.planned_production_date.split('T')[0]}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`text-sm font-medium ${task.days_until_due < 0 ? 'text-red-600' : task.days_until_due <= 7 ? 'text-yellow-600' : 'text-gray-900'}`}>
                        {task.days_until_due < 0 ? `${Math.abs(task.days_until_due)} days overdue` : `${task.days_until_due} days`}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {task.validation_status ? (
                        <span className={`px-2 py-1 text-xs font-semibold rounded ${task.validation_status === 'Approved' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {task.validation_status}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">No validation</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(task)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {task.status === 'PENDING' && (
                        <button
                          onClick={() => openConfirmModal(task)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Confirm Deployment
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium">About Deployment Confirmations</p>
              <p className="mt-1">
                {user?.role === 'Admin' ? (
                  <>
                    This page shows all pending deployment confirmations across the organization.
                    Model owners and developers are responsible for confirming when model versions are deployed to production.
                    Deployments should ideally occur after validation has been approved. If a deployment must occur before validation approval,
                    a justification is required and the deployment will be flagged for compliance review.
                  </>
                ) : (
                  <>
                    As a model owner or developer, you're responsible for confirming when your model versions are deployed to production.
                    Deployments should ideally occur after validation has been approved. If you must deploy before validation approval,
                    you'll need to provide a justification, and the deployment will be flagged for compliance review.
                  </>
                )}
              </p>
              <p className="mt-2 text-xs text-blue-700">
                <strong>Note:</strong> Confirm deployments promptly to maintain accurate compliance records.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Confirm Deployment Modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
            <h2 className="text-2xl font-bold mb-4">Confirm Deployment</h2>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                <strong>Model:</strong> {confirmModal.model_name}
              </p>
              <p className="text-sm text-gray-600 mb-4">
                <strong>Version:</strong> {confirmModal.version_number}
              </p>
            </div>

            {validationWarning && (
              <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-400 rounded">
                <h3 className="font-bold text-yellow-900 mb-2">⚠️ Validation Not Approved</h3>
                <p className="text-sm text-yellow-800 mb-3">{validationWarning}</p>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Override Justification *
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Enter justification for deploying before validation approval..."
                  rows={3}
                  className="w-full px-3 py-2 border border-yellow-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  required={!!validationWarning}
                />
                <p className="text-xs text-yellow-700 mt-1">
                  This deployment will be flagged for compliance review
                </p>
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Actual Deployment Date *
              </label>
              <input
                type="date"
                value={actualDate}
                onChange={(e) => setActualDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Deployment Notes (Optional)
              </label>
              <textarea
                value={confirmNotes}
                onChange={(e) => setConfirmNotes(e.target.value)}
                placeholder="Enter any notes about this deployment..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmModal(null)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={confirmLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className={`px-4 py-2 rounded-md text-white ${validationWarning ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-blue-600 hover:bg-blue-700'} disabled:bg-gray-400`}
                disabled={confirmLoading || !actualDate}
              >
                {confirmLoading ? 'Confirming...' : validationWarning ? 'Confirm with Override' : 'Confirm Deployment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default MyDeploymentTasksPage;

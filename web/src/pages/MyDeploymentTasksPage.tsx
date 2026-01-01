import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { deploymentsApi, BulkConfirmRequest, BulkAdjustRequest, BulkCancelRequest } from '../api/deployments';
import { canViewAdminDashboard } from '../utils/roleUtils';

interface DeploymentTask {
  task_id: number;
  model_name: string;
  version_number: string;
  region_code: string | null;
  region_name: string | null;
  region_id: number | null;
  planned_production_date: string;
  actual_production_date: string | null;
  days_until_due: number;
  status: string;
  assigned_to_name: string;
  deployed_before_validation_approved: boolean;
  validation_status: string | null;
  requires_regional_approval: boolean; // Issue 6: Lock icon indicator
}

interface ConfirmModalData {
  task_id: number;
  model_name: string;
  version_number: string;
  validation_status: string | null;
}

const MyDeploymentTasksPage = () => {
  const { user } = useAuth();
  const canViewAdminDashboardFlag = canViewAdminDashboard(user);
  const [tasks, setTasks] = useState<DeploymentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'overdue' | 'due-today' | 'this-week' | 'due-soon' | 'upcoming'>('all');

  // Issue 6: Search and date range state
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRangeStart, setDateRangeStart] = useState('');
  const [dateRangeEnd, setDateRangeEnd] = useState('');

  // Bulk selection state
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set());

  // Confirm modal state (single task)
  const [confirmModal, setConfirmModal] = useState<ConfirmModalData | null>(null);
  const [actualDate, setActualDate] = useState('');
  const [confirmNotes, setConfirmNotes] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [validationWarning, setValidationWarning] = useState<string | null>(null);

  // Bulk confirm modal state
  const [bulkConfirmModal, setBulkConfirmModal] = useState(false);
  const [bulkActualDate, setBulkActualDate] = useState('');
  const [bulkConfirmNotes, setBulkConfirmNotes] = useState('');
  const [bulkOverrideReason, setBulkOverrideReason] = useState('');
  const [bulkConfirmLoading, setBulkConfirmLoading] = useState(false);

  // Bulk adjust dates modal state
  const [bulkAdjustModal, setBulkAdjustModal] = useState(false);
  const [bulkNewDate, setBulkNewDate] = useState('');
  const [bulkAdjustReason, setBulkAdjustReason] = useState('');
  const [bulkAdjustLoading, setBulkAdjustLoading] = useState(false);

  // Bulk cancel modal state
  const [bulkCancelModal, setBulkCancelModal] = useState(false);
  const [bulkCancelReason, setBulkCancelReason] = useState('');
  const [bulkCancelLoading, setBulkCancelLoading] = useState(false);

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

      // Apply status filter
      let passesStatusFilter = true;
      switch (filter) {
        case 'overdue':
          passesStatusFilter = daysUntilDue < 0;
          break;
        case 'due-today':
          passesStatusFilter = daysUntilDue === 0;
          break;
        case 'this-week':
          passesStatusFilter = daysUntilDue >= 0 && daysUntilDue <= 7;
          break;
        case 'due-soon':
          passesStatusFilter = daysUntilDue >= 0 && daysUntilDue <= 7;
          break;
        case 'upcoming':
          passesStatusFilter = daysUntilDue > 7;
          break;
        default:
          passesStatusFilter = true;
      }
      if (!passesStatusFilter) return false;

      // Apply search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          task.model_name?.toLowerCase().includes(query) ||
          task.version_number?.toLowerCase().includes(query) ||
          task.region_code?.toLowerCase().includes(query) ||
          task.region_name?.toLowerCase().includes(query);
        if (!matchesSearch) return false;
      }

      // Apply date range filter
      if (dateRangeStart || dateRangeEnd) {
        const taskDate = new Date(task.planned_production_date);
        if (dateRangeStart) {
          const startDate = new Date(dateRangeStart);
          if (taskDate < startDate) return false;
        }
        if (dateRangeEnd) {
          const endDate = new Date(dateRangeEnd);
          if (taskDate > endDate) return false;
        }
      }

      return true;
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

  // Bulk selection helpers
  const toggleTaskSelection = (taskId: number) => {
    setSelectedTasks(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedTasks.size === filteredTasks.length) {
      setSelectedTasks(new Set());
    } else {
      setSelectedTasks(new Set(filteredTasks.map(t => t.task_id)));
    }
  };

  const clearSelection = () => {
    setSelectedTasks(new Set());
  };

  const getSelectedTasksData = () => {
    return tasks.filter(t => selectedTasks.has(t.task_id));
  };

  const hasUnvalidatedSelectedTasks = () => {
    const selectedData = getSelectedTasksData();
    return selectedData.some(t => t.validation_status && t.validation_status !== 'Approved');
  };

  // Bulk confirm handler
  const openBulkConfirmModal = () => {
    setBulkActualDate(new Date().toISOString().split('T')[0]);
    setBulkConfirmNotes('');
    setBulkOverrideReason('');
    setBulkConfirmModal(true);
  };

  const handleBulkConfirm = async () => {
    if (selectedTasks.size === 0) return;

    const requiresOverride = hasUnvalidatedSelectedTasks();
    if (requiresOverride && !bulkOverrideReason.trim()) {
      alert('Override reason is required when confirming deployments before validation approval');
      return;
    }

    try {
      setBulkConfirmLoading(true);
      const request: BulkConfirmRequest = {
        task_ids: Array.from(selectedTasks),
        actual_production_date: bulkActualDate,
        confirmation_notes: bulkConfirmNotes || undefined,
        validation_override_reason: requiresOverride ? bulkOverrideReason : undefined
      };
      const result = await deploymentsApi.bulkConfirm(request);

      if (result.data.failed.length > 0) {
        alert(`Confirmed ${result.data.succeeded.length} tasks. ${result.data.failed.length} failed:\n${result.data.failed.map(f => f.error).join('\n')}`);
      }

      setBulkConfirmModal(false);
      clearSelection();
      fetchTasks();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to confirm deployments');
    } finally {
      setBulkConfirmLoading(false);
    }
  };

  // Bulk adjust dates handler
  const openBulkAdjustModal = () => {
    setBulkNewDate('');
    setBulkAdjustReason('');
    setBulkAdjustModal(true);
  };

  const handleBulkAdjust = async () => {
    if (selectedTasks.size === 0 || !bulkNewDate) return;

    try {
      setBulkAdjustLoading(true);
      const request: BulkAdjustRequest = {
        task_ids: Array.from(selectedTasks),
        new_planned_date: bulkNewDate,
        adjustment_reason: bulkAdjustReason || undefined
      };
      const result = await deploymentsApi.bulkAdjust(request);

      if (result.data.failed.length > 0) {
        alert(`Adjusted ${result.data.succeeded.length} tasks. ${result.data.failed.length} failed:\n${result.data.failed.map(f => f.error).join('\n')}`);
      }

      setBulkAdjustModal(false);
      clearSelection();
      fetchTasks();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to adjust dates');
    } finally {
      setBulkAdjustLoading(false);
    }
  };

  // Bulk cancel handler
  const openBulkCancelModal = () => {
    setBulkCancelReason('');
    setBulkCancelModal(true);
  };

  const handleBulkCancel = async () => {
    if (selectedTasks.size === 0) return;

    try {
      setBulkCancelLoading(true);
      const request: BulkCancelRequest = {
        task_ids: Array.from(selectedTasks),
        cancellation_reason: bulkCancelReason || undefined
      };
      const result = await deploymentsApi.bulkCancel(request);

      if (result.data.failed.length > 0) {
        alert(`Cancelled ${result.data.succeeded.length} tasks. ${result.data.failed.length} failed:\n${result.data.failed.map(f => f.error).join('\n')}`);
      }

      setBulkCancelModal(false);
      clearSelection();
      fetchTasks();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel tasks');
    } finally {
      setBulkCancelLoading(false);
    }
  };

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
        <div className="flex flex-wrap gap-2">
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
            onClick={() => setFilter('due-today')}
            className={`px-4 py-2 rounded ${filter === 'due-today' ? 'bg-orange-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Due Today ({tasks.filter(t => t.status === 'PENDING' && t.days_until_due === 0).length})
          </button>
          <button
            onClick={() => setFilter('this-week')}
            className={`px-4 py-2 rounded ${filter === 'this-week' ? 'bg-yellow-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            This Week ({tasks.filter(t => t.status === 'PENDING' && t.days_until_due >= 0 && t.days_until_due <= 7).length})
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

        {/* Search and Date Range */}
        <div className="flex flex-wrap gap-4 items-end">
          {/* Search Box */}
          <div className="flex-1 min-w-64">
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              placeholder="Search by model, version, or region..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {/* Date Range */}
          <div className="flex gap-2 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
              <input
                type="date"
                value={dateRangeStart}
                onChange={(e) => setDateRangeStart(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
              <input
                type="date"
                value={dateRangeEnd}
                onChange={(e) => setDateRangeEnd(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            {(searchQuery || dateRangeStart || dateRangeEnd) && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setDateRangeStart('');
                  setDateRangeEnd('');
                }}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 underline"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Bulk Action Bar */}
        {selectedTasks.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-blue-800">
                {selectedTasks.size} task{selectedTasks.size > 1 ? 's' : ''} selected
              </span>
              <button
                onClick={clearSelection}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Clear selection
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={openBulkConfirmModal}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium"
              >
                Confirm Selected ({selectedTasks.size})
              </button>
              <button
                onClick={openBulkAdjustModal}
                className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm font-medium"
              >
                Adjust Dates
              </button>
              <button
                onClick={openBulkCancelModal}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm font-medium"
              >
                Cancel Selected
              </button>
            </div>
          </div>
        )}

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
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    <input
                      type="checkbox"
                      checked={filteredTasks.length > 0 && selectedTasks.size === filteredTasks.length}
                      onChange={toggleSelectAll}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      title={selectedTasks.size === filteredTasks.length ? "Deselect all" : "Select all"}
                    />
                  </th>
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
                    <td className="px-4 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={selectedTasks.has(task.task_id)}
                        onChange={() => toggleTaskSelection(task.task_id)}
                        className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                    </td>
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
                {canViewAdminDashboardFlag ? (
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

      {/* Bulk Confirm Modal */}
      {bulkConfirmModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Confirm Multiple Deployments</h2>

            <div className="mb-4 bg-gray-50 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-700 mb-2">Selected Deployments ({selectedTasks.size}):</p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {getSelectedTasksData().map(task => (
                  <div key={task.task_id} className="text-sm text-gray-600 flex items-center gap-2">
                    <span>{task.model_name} v{task.version_number}</span>
                    <span className="text-gray-400">→</span>
                    <span>{task.region_code || 'Global'}</span>
                    {task.requires_regional_approval && (
                      <span className="text-yellow-500" title="Regional approval required">🔒</span>
                    )}
                    {task.validation_status && task.validation_status !== 'Approved' && (
                      <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">
                        {task.validation_status}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              {/* Footer note for regional approvals */}
              {getSelectedTasksData().some(t => t.requires_regional_approval) && (
                <p className="text-xs text-yellow-700 mt-2 pt-2 border-t border-gray-200">
                  🔒 Regional approval will be requested for regions not covered by validation scope
                </p>
              )}
            </div>

            {hasUnvalidatedSelectedTasks() && (
              <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-400 rounded">
                <h3 className="font-bold text-yellow-900 mb-2">⚠️ Some Validations Not Approved</h3>
                <p className="text-sm text-yellow-800 mb-3">
                  One or more selected deployments have a validation that is not yet approved.
                  An override justification is required.
                </p>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Override Justification *
                </label>
                <textarea
                  value={bulkOverrideReason}
                  onChange={(e) => setBulkOverrideReason(e.target.value)}
                  placeholder="Enter justification for deploying before validation approval..."
                  rows={3}
                  className="w-full px-3 py-2 border border-yellow-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  required
                />
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Actual Deployment Date *
              </label>
              <input
                type="date"
                value={bulkActualDate}
                onChange={(e) => setBulkActualDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">This date will be applied to all selected deployments</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirmation Notes (Optional)
              </label>
              <textarea
                value={bulkConfirmNotes}
                onChange={(e) => setBulkConfirmNotes(e.target.value)}
                placeholder="Enter any notes about these deployments..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setBulkConfirmModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={bulkConfirmLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleBulkConfirm}
                className={`px-4 py-2 rounded-md text-white ${hasUnvalidatedSelectedTasks() ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'} disabled:bg-gray-400`}
                disabled={bulkConfirmLoading || !bulkActualDate || (hasUnvalidatedSelectedTasks() && !bulkOverrideReason.trim())}
              >
                {bulkConfirmLoading ? 'Confirming...' : `Confirm ${selectedTasks.size} Deployment${selectedTasks.size > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Adjust Dates Modal */}
      {bulkAdjustModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Adjust Planned Dates</h2>

            <div className="mb-4 bg-gray-50 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-700 mb-2">Selected Deployments ({selectedTasks.size}):</p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {getSelectedTasksData().map(task => (
                  <div key={task.task_id} className="text-sm text-gray-600 flex items-center gap-2">
                    <span>{task.model_name} v{task.version_number}</span>
                    <span className="text-gray-400">→</span>
                    <span>{task.region_code || 'Global'}</span>
                    <span className="text-gray-400">(currently: {task.planned_production_date.split('T')[0]})</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Planned Date *
              </label>
              <input
                type="date"
                value={bulkNewDate}
                onChange={(e) => setBulkNewDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">This date will be applied to all selected tasks</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Adjustment Reason (Optional)
              </label>
              <textarea
                value={bulkAdjustReason}
                onChange={(e) => setBulkAdjustReason(e.target.value)}
                placeholder="Explain why the dates are being adjusted..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setBulkAdjustModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={bulkAdjustLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleBulkAdjust}
                className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-400"
                disabled={bulkAdjustLoading || !bulkNewDate}
              >
                {bulkAdjustLoading ? 'Adjusting...' : `Adjust ${selectedTasks.size} Date${selectedTasks.size > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Cancel Modal */}
      {bulkCancelModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4 text-red-700">Cancel Deployments</h2>

            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm font-medium text-red-700 mb-2">
                You are about to cancel {selectedTasks.size} deployment task{selectedTasks.size > 1 ? 's' : ''}:
              </p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {getSelectedTasksData().map(task => (
                  <div key={task.task_id} className="text-sm text-red-600 flex items-center gap-2">
                    <span>{task.model_name} v{task.version_number}</span>
                    <span className="text-red-400">→</span>
                    <span>{task.region_code || 'Global'}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cancellation Reason (Optional)
              </label>
              <textarea
                value={bulkCancelReason}
                onChange={(e) => setBulkCancelReason(e.target.value)}
                placeholder="Explain why these deployments are being cancelled..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setBulkCancelModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={bulkCancelLoading}
              >
                Keep Tasks
              </button>
              <button
                onClick={handleBulkCancel}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400"
                disabled={bulkCancelLoading}
              >
                {bulkCancelLoading ? 'Cancelling...' : `Cancel ${selectedTasks.size} Task${selectedTasks.size > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default MyDeploymentTasksPage;

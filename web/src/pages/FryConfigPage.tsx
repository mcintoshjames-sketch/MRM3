import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';
import { useAuth } from '../contexts/AuthContext';

interface FryLineItem {
  line_item_id: number;
  line_item_text: string;
  sort_order: number;
}

interface FryMetricGroup {
  metric_group_id: number;
  metric_group_name: string;
  model_driven: boolean;
  is_active: boolean;
  rationale?: string;
  line_items?: FryLineItem[];
}

interface FrySchedule {
  schedule_id: number;
  schedule_code: string;
  is_active: boolean;
  description?: string;
  metric_groups?: FryMetricGroup[];
}

interface FryReport {
  report_id: number;
  report_code: string;
  description?: string;
  is_active: boolean;
  schedules?: FrySchedule[];
}

const FryConfigPage: React.FC = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState<FryReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<FryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedReports, setExpandedReports] = useState<Set<number>>(new Set());
  const [expandedSchedules, setExpandedSchedules] = useState<Set<number>>(new Set());
  const [expandedMetricGroups, setExpandedMetricGroups] = useState<Set<number>>(new Set());
  const [editingItem, setEditingItem] = useState<any>(null);
  const [editMode, setEditMode] = useState<'report' | 'schedule' | 'metric_group' | 'line_item' | null>(null);

  const isAdmin = user?.role === 'Admin';

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await client.get('/fry/reports');
      setReports(response.data);
    } catch (error) {
      console.error('Error fetching FRY reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReportDetails = async (reportId: number) => {
    try {
      const response = await client.get(`/fry/reports/${reportId}`);
      setSelectedReport(response.data);
      setExpandedReports(new Set([...expandedReports, reportId]));
    } catch (error) {
      console.error('Error fetching report details:', error);
    }
  };

  const toggleReport = async (reportId: number) => {
    if (expandedReports.has(reportId)) {
      const newExpanded = new Set(expandedReports);
      newExpanded.delete(reportId);
      setExpandedReports(newExpanded);
    } else {
      await fetchReportDetails(reportId);
    }
  };

  const toggleSchedule = (scheduleId: number) => {
    const newExpanded = new Set(expandedSchedules);
    if (newExpanded.has(scheduleId)) {
      newExpanded.delete(scheduleId);
    } else {
      newExpanded.add(scheduleId);
    }
    setExpandedSchedules(newExpanded);
  };

  const toggleMetricGroup = (metricGroupId: number) => {
    const newExpanded = new Set(expandedMetricGroups);
    if (newExpanded.has(metricGroupId)) {
      newExpanded.delete(metricGroupId);
    } else {
      newExpanded.add(metricGroupId);
    }
    setExpandedMetricGroups(newExpanded);
  };

  const handleEditMetricGroup = (metricGroup: FryMetricGroup) => {
    setEditingItem(metricGroup);
    setEditMode('metric_group');
  };

  const handleSaveMetricGroup = async () => {
    if (!editingItem) return;

    try {
      await client.patch(`/fry/metric-groups/${editingItem.metric_group_id}`, {
        metric_group_name: editingItem.metric_group_name,
        model_driven: editingItem.model_driven,
        rationale: editingItem.rationale,
        is_active: editingItem.is_active
      });

      // Refresh report details
      if (selectedReport) {
        await fetchReportDetails(selectedReport.report_id);
      }

      setEditingItem(null);
      setEditMode(null);
    } catch (error) {
      console.error('Error saving metric group:', error);
      alert('Failed to save metric group');
    }
  };

  const handleCancelEdit = () => {
    setEditingItem(null);
    setEditMode(null);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="text-gray-500">Loading FRY 14 Configuration...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="sm:flex sm:items-center">
          <div className="sm:flex-auto">
            <h1 className="text-2xl font-semibold text-gray-900">FRY 14 Reporting Configuration</h1>
            <p className="mt-2 text-sm text-gray-700">
              Manage the Federal Reserve Board FR Y-14 reporting structure including schedules, metric groups, and line items.
            </p>
          </div>
        </div>

        <div className="mt-8">
          {reports.length === 0 ? (
            <div className="text-center py-12 bg-white shadow rounded-lg">
              <p className="text-gray-500">No FRY reports configured.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {reports.map((report) => (
                <div key={report.report_id} className="bg-white shadow rounded-lg overflow-hidden">
                  {/* Report Header */}
                  <div
                    className="px-6 py-4 border-b border-gray-200 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                    onClick={() => toggleReport(report.report_id)}
                  >
                    <div className="flex items-center">
                      <svg
                        className={`h-5 w-5 text-gray-400 transition-transform ${
                          expandedReports.has(report.report_id) ? 'transform rotate-90' : ''
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      <div className="ml-3">
                        <h3 className="text-lg font-medium text-gray-900">{report.report_code}</h3>
                        <p className="text-sm text-gray-500">{report.description}</p>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        report.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {report.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  {/* Schedules (expanded view) */}
                  {expandedReports.has(report.report_id) && selectedReport?.report_id === report.report_id && (
                    <div className="px-6 py-4 bg-gray-50">
                      {selectedReport.schedules && selectedReport.schedules.length > 0 ? (
                        <div className="space-y-3">
                          {selectedReport.schedules.map((schedule) => (
                            <div key={schedule.schedule_id} className="bg-white rounded-md shadow-sm overflow-hidden">
                              {/* Schedule Header */}
                              <div
                                className="px-4 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 flex items-center"
                                onClick={() => toggleSchedule(schedule.schedule_id)}
                              >
                                <svg
                                  className={`h-4 w-4 text-gray-400 transition-transform ${
                                    expandedSchedules.has(schedule.schedule_id) ? 'transform rotate-90' : ''
                                  }`}
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                                <div className="ml-2">
                                  <h4 className="text-sm font-medium text-gray-900">{schedule.schedule_code}</h4>
                                  {schedule.description && (
                                    <p className="text-xs text-gray-500">{schedule.description}</p>
                                  )}
                                </div>
                              </div>

                              {/* Metric Groups */}
                              {expandedSchedules.has(schedule.schedule_id) && schedule.metric_groups && (
                                <div className="px-4 py-3 bg-gray-50">
                                  {schedule.metric_groups.map((metricGroup) => (
                                    <div key={metricGroup.metric_group_id} className="mb-3 last:mb-0">
                                      {/* Metric Group Header */}
                                      <div className="bg-white rounded-md p-3 shadow-sm">
                                        <div className="flex items-start justify-between">
                                          <div
                                            className="flex-1 cursor-pointer"
                                            onClick={() => toggleMetricGroup(metricGroup.metric_group_id)}
                                          >
                                            <div className="flex items-center">
                                              <svg
                                                className={`h-4 w-4 text-gray-400 transition-transform ${
                                                  expandedMetricGroups.has(metricGroup.metric_group_id)
                                                    ? 'transform rotate-90'
                                                    : ''
                                                }`}
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                              >
                                                <path
                                                  strokeLinecap="round"
                                                  strokeLinejoin="round"
                                                  strokeWidth={2}
                                                  d="M9 5l7 7-7 7"
                                                />
                                              </svg>
                                              <h5 className="ml-2 text-sm font-medium text-gray-900">
                                                {metricGroup.metric_group_name}
                                              </h5>
                                              <span
                                                className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${
                                                  metricGroup.model_driven
                                                    ? 'bg-blue-100 text-blue-800'
                                                    : 'bg-gray-100 text-gray-600'
                                                }`}
                                              >
                                                {metricGroup.model_driven ? 'Model-Driven' : 'Non-Model'}
                                              </span>
                                            </div>
                                          </div>
                                          {isAdmin && (
                                            <button
                                              onClick={() => handleEditMetricGroup(metricGroup)}
                                              className="ml-2 text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                              Edit
                                            </button>
                                          )}
                                        </div>

                                        {metricGroup.rationale && (
                                          <p className="mt-2 text-xs text-gray-600 ml-6">{metricGroup.rationale}</p>
                                        )}

                                        {/* Line Items */}
                                        {expandedMetricGroups.has(metricGroup.metric_group_id) &&
                                          metricGroup.line_items &&
                                          metricGroup.line_items.length > 0 && (
                                            <div className="mt-3 ml-6 pl-3 border-l-2 border-gray-200">
                                              <h6 className="text-xs font-medium text-gray-700 mb-2">Line Items:</h6>
                                              <ul className="space-y-1">
                                                {metricGroup.line_items.map((lineItem, idx) => (
                                                  <li key={lineItem.line_item_id} className="text-xs text-gray-600">
                                                    {idx + 1}. {lineItem.line_item_text}
                                                  </li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No schedules available for this report.</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Edit Modal */}
        {editMode === 'metric_group' && editingItem && (
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Metric Group</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Metric Group Name</label>
                  <input
                    type="text"
                    value={editingItem.metric_group_name}
                    onChange={(e) => setEditingItem({ ...editingItem, metric_group_name: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={editingItem.model_driven}
                      onChange={(e) => setEditingItem({ ...editingItem, model_driven: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Model-Driven</span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={editingItem.is_active}
                      onChange={(e) => setEditingItem({ ...editingItem, is_active: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Active</span>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Rationale</label>
                  <textarea
                    value={editingItem.rationale || ''}
                    onChange={(e) => setEditingItem({ ...editingItem, rationale: e.target.value })}
                    rows={4}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={handleCancelEdit}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveMetricGroup}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default FryConfigPage;

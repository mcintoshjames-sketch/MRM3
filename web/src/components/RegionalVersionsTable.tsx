import React, { useEffect, useState } from 'react';
import api from '../api/client';

interface RegionalVersion {
  region_id: number;
  region_code: string;
  region_name: string;
  current_version_id: number | null;
  version_number: string | null;
  deployed_at: string | null;
  deployment_notes: string | null;
  is_same_as_global: boolean;
  is_regional_override: boolean;
}

interface GlobalVersion {
  version_id: number;
  version_number: string;
  change_description: string;
  scope: string;
  status: string;
  created_at: string;
}

interface RegionalVersionsData {
  model_id: number;
  model_name: string;
  global_version: GlobalVersion | null;
  regional_versions: RegionalVersion[];
}

interface RegionalVersionsTableProps {
  modelId: number;
  refreshTrigger?: number;
}

const RegionalVersionsTable: React.FC<RegionalVersionsTableProps> = ({ modelId, refreshTrigger }) => {
  const [data, setData] = useState<RegionalVersionsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRegionalVersions();
  }, [modelId, refreshTrigger]);

  const fetchRegionalVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/models/${modelId}/regional-versions`);
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load regional versions');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Regional Version Deployments</h3>
        <p className="text-gray-500">Loading regional deployment status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Regional Version Deployments</h3>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { global_version, regional_versions } = data;

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Regional Version Deployments</h3>

      {/* Global Version Info */}
      {global_version && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-semibold text-blue-900 mb-2">Global Active Version</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Version:</span>{' '}
              <span className="font-medium">{global_version.version_number}</span>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>{' '}
              <span className="font-medium">{global_version.status}</span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-600">Description:</span>{' '}
              <span className="font-medium">{global_version.change_description}</span>
            </div>
          </div>
        </div>
      )}

      {/* Regional Versions Table */}
      {regional_versions.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No regional deployments found. This model has not been assigned to any regions yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Region
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Current Version
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Deployed At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Deployment Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Notes
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {regional_versions.map((rv) => (
                <tr key={rv.region_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="font-medium text-gray-900">{rv.region_name}</div>
                      <div className="text-sm text-gray-500">{rv.region_code}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {rv.version_number ? (
                      <span className="font-medium text-gray-900">{rv.version_number}</span>
                    ) : (
                      <span className="text-gray-400 italic">None</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {rv.deployed_at ? rv.deployed_at.split('T')[0] : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {rv.is_regional_override ? (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">
                        Regional Override
                      </span>
                    ) : rv.is_same_as_global ? (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                        Global Version
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                        No Version
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                    {rv.deployment_notes || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Info Note */}
      <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
        <strong>Note:</strong> Regional overrides allow specific regions to run different versions
        of the model. If no regional override is set, the region uses the global active version.
      </div>
    </div>
  );
};

export default RegionalVersionsTable;

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

interface ModelVersion {
  version_id: number;
  model_id: number;
  version_number: string;
  change_type: string;
  change_type_id: number | null;
  change_type_name: string | null;
  change_category_name: string | null;
  change_description: string;
  scope: string;
  affected_region_ids: number[] | null;
  planned_production_date: string | null;
  actual_production_date: string | null;
  production_date: string | null;
  status: string;
  created_by_id: number;
  created_by_name: string | null;
  created_at: string;
  validation_request_id: number | null;
}

interface Region {
  region_id: number;
  code: string;
  name: string;
}

interface ValidationRequest {
  request_id: number;
  validation_type: { label: string };
  priority: { label: string };
  current_status: { label: string };
  target_completion_date: string;
}

const ModelChangeRecordPage = () => {
  const { model_id, version_id } = useParams<{ model_id: string; version_id: string }>();
  const navigate = useNavigate();
  const [version, setVersion] = useState<ModelVersion | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [validationRequest, setValidationRequest] = useState<ValidationRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [model_id, version_id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch version details
      const versionRes = await api.get(`/models/${model_id}/versions`);
      const versionData = versionRes.data.find((v: ModelVersion) => v.version_id === parseInt(version_id || '0'));

      if (!versionData) {
        setError('Version not found');
        return;
      }

      setVersion(versionData);

      // Fetch all regions
      const regionsRes = await api.get('/regions/');
      setRegions(regionsRes.data);

      // Fetch validation request if exists
      if (versionData.validation_request_id) {
        try {
          const valReqRes = await api.get(`/validation-workflow/requests/${versionData.validation_request_id}`);
          setValidationRequest(valReqRes.data);
        } catch (err) {
          console.warn('Could not load validation request:', err);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load change record');
    } finally {
      setLoading(false);
    }
  };

  const getAffectedRegions = () => {
    if (!version || !version.affected_region_ids || version.scope !== 'REGIONAL') {
      return [];
    }
    return regions.filter(r => version.affected_region_ids?.includes(r.region_id));
  };

  const getScopeColor = (scope: string) => {
    return scope === 'GLOBAL' ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'DRAFT': 'bg-gray-100 text-gray-800',
      'IN_VALIDATION': 'bg-yellow-100 text-yellow-800',
      'APPROVED': 'bg-green-100 text-green-800',
      'ACTIVE': 'bg-blue-100 text-blue-800',
      'SUPERSEDED': 'bg-purple-100 text-purple-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <p className="text-gray-500">Loading change record...</p>
        </div>
      </Layout>
    );
  }

  if (error || !version) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error || 'Change record not found'}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 text-blue-600 hover:text-blue-800 hover:underline"
          >
            ← Go Back
          </button>
        </div>
      </Layout>
    );
  }

  const affectedRegions = getAffectedRegions();

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate(`/models/${model_id}`)}
              className="text-blue-600 hover:text-blue-800 hover:underline mb-2"
            >
              ← Back to Model
            </button>
            <h2 className="text-2xl font-bold text-gray-900">
              Model Change Record: Version {version.version_number}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Created {version.created_at.split('T')[0]} by {version.created_by_name || 'Unknown'}
            </p>
          </div>
          <span className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(version.status)}`}>
            {version.status}
          </span>
        </div>

        {/* Version Details */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Version Details</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Version Number</label>
              <p className="text-gray-900 font-semibold">{version.version_number}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Change Type</label>
              <p className="text-gray-900">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  version.change_type === 'MAJOR' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}>
                  {version.change_type}
                </span>
                {version.change_type_name && (
                  <span className="ml-2 text-sm text-gray-600">
                    ({version.change_category_name}: {version.change_type_name})
                  </span>
                )}
              </p>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Change Description</label>
              <p className="text-gray-900">{version.change_description}</p>
            </div>
          </div>
        </div>

        {/* Scope and Regional Information */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Scope and Regional Impact</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getScopeColor(version.scope)}`}>
                {version.scope}
              </span>
              <p className="text-xs text-gray-500 mt-2">
                {version.scope === 'GLOBAL'
                  ? 'This change affects all regions'
                  : 'This change affects specific regions only'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Affected Regions</label>
              {version.scope === 'GLOBAL' ? (
                <p className="text-gray-600 text-sm">All regions</p>
              ) : affectedRegions.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {affectedRegions.map(region => (
                    <span key={region.region_id} className="px-2 py-1 bg-orange-50 border border-orange-200 rounded text-sm">
                      {region.name} ({region.code})
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm italic">No regions specified</p>
              )}
            </div>
          </div>
        </div>

        {/* Production Dates */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Production Timeline</h3>
          <div className="grid grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Planned Production Date</label>
              <p className="text-gray-900">
                {version.planned_production_date
                  ? version.planned_production_date.split('T')[0]
                  : '—'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Actual Production Date</label>
              <p className="text-gray-900">
                {version.actual_production_date
                  ? version.actual_production_date.split('T')[0]
                  : '—'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              {version.actual_production_date ? (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm font-medium">
                  Deployed
                </span>
              ) : version.planned_production_date ? (
                <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm font-medium">
                  Planned
                </span>
              ) : (
                <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-sm font-medium">
                  Not Scheduled
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Validation Request */}
        {version.validation_request_id && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Associated Validation Request</h3>
            {validationRequest ? (
              <div>
                <div className="grid grid-cols-2 gap-6 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Request ID</label>
                    <Link
                      to={`/validation-workflow`}
                      className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                    >
                      #{validationRequest.request_id}
                    </Link>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    <p className="text-gray-900">{validationRequest.current_status.label}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                    <p className="text-gray-900">{validationRequest.validation_type.label}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                    <p className="text-gray-900">{validationRequest.priority.label}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Target Completion</label>
                    <p className="text-gray-900">
                      {validationRequest.target_completion_date.split('T')[0]}
                    </p>
                  </div>
                </div>
                <Link
                  to={`/validation-workflow`}
                  className="text-blue-600 hover:text-blue-800 hover:underline text-sm"
                >
                  View Full Validation Request →
                </Link>
              </div>
            ) : (
              <p className="text-gray-500">Validation request #{version.validation_request_id}</p>
            )}
          </div>
        )}

        {/* Info Note */}
        {version.change_type === 'MAJOR' && !version.validation_request_id && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800 text-sm">
              <strong>Note:</strong> This is a MAJOR change but no validation request was automatically created.
              This may be because the version was created before auto-validation was implemented.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ModelChangeRecordPage;

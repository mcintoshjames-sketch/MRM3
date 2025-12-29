import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { linkChangeToAttestationIfPresent } from '../api/attestation';

interface Model {
  model_id: number;
  model_name: string;
  owner_id: number;
  owner_name?: string;
  risk_tier?: string;
  status?: string;
  regions?: { region_id: number; code: string; name: string }[];
}

interface TaxonomyValue {
  value_id: number;
  code: string;
  label: string;
}

interface ReplacementModelInfo {
  model_id: number;
  model_name: string;
  implementation_date?: string;
  status?: string;
}

interface Approval {
  approval_id: number;
  request_id: number;
  approver_type: string;
  region_id?: number;
  region?: { region_id: number; code: string; name: string };
  approved_by_id?: number;
  approved_by?: { full_name: string };
  approved_at?: string;
  is_approved?: boolean;
  comment?: string;
}

interface StatusHistory {
  history_id: number;
  old_status?: string;
  new_status: string;
  changed_by?: { full_name: string };
  changed_at: string;
  notes?: string;
}

interface DecommissioningRequest {
  request_id: number;
  model_id: number;
  model?: Model;
  status: string;
  reason_id: number;
  reason?: TaxonomyValue;
  replacement_model_id?: number;
  replacement_model?: ReplacementModelInfo;
  last_production_date: string;
  gap_justification?: string;
  gap_days?: number;
  archive_location: string;
  downstream_impact_verified: boolean;
  created_at: string;
  created_by_id: number;
  created_by?: { full_name: string };
  validator_reviewed_by_id?: number;
  validator_reviewed_by?: { full_name: string };
  validator_reviewed_at?: string;
  validator_comment?: string;
  // Owner review fields (required if owner != requestor)
  owner_approval_required: boolean;
  owner_reviewed_by_id?: number;
  owner_reviewed_by?: { full_name: string };
  owner_reviewed_at?: string;
  owner_comment?: string;
  final_reviewed_at?: string;
  rejection_reason?: string;
  status_history: StatusHistory[];
  approvals: Approval[];
}

interface ModelListItem {
  model_id: number;
  model_name: string;
  status: string;
}

interface DownstreamDependency {
  id: number;
  model_id: number;
  model_name: string;
  dependency_type: string;
  dependency_type_id: number;
  description?: string;
  is_active: boolean;
}

const REASONS_REQUIRING_REPLACEMENT = ['REPLACEMENT', 'CONSOLIDATION'];

const DecommissioningRequestPage = () => {
  const { id: modelIdParam } = useParams<{ id: string }>();
  const modelId = parseInt(modelIdParam || '0');
  const navigate = useNavigate();
  const { user } = useAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<Model | null>(null);
  const [existingRequest, setExistingRequest] = useState<DecommissioningRequest | null>(null);
  const [reasons, setReasons] = useState<TaxonomyValue[]>([]);
  const [allModels, setAllModels] = useState<ModelListItem[]>([]);
  const [downstreamDependencies, setDownstreamDependencies] = useState<DownstreamDependency[]>([]);

  // Form state for creating new request
  const [formMode, setFormMode] = useState<'view' | 'create'>('view');
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [replacementModelId, setReplacementModelId] = useState<number | null>(null);
  const [replacementImplDate, setReplacementImplDate] = useState('');
  const [lastProductionDate, setLastProductionDate] = useState('');
  const [gapJustification, setGapJustification] = useState('');
  const [archiveLocation, setArchiveLocation] = useState('');
  const [downstreamVerified, setDownstreamVerified] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Replacement model implementation date check
  const [replacementHasDate, setReplacementHasDate] = useState<boolean | null>(null);
  const [replacementCurrentDate, setReplacementCurrentDate] = useState<string | null>(null);
  const [gapDays, setGapDays] = useState<number | null>(null);

  // Replacement model search state
  const [replacementSearch, setReplacementSearch] = useState('');
  const [showReplacementDropdown, setShowReplacementDropdown] = useState(false);
  const replacementDropdownRef = useRef<HTMLDivElement>(null);

  // Validator review modal state
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewApproved, setReviewApproved] = useState(true);
  const [reviewComment, setReviewComment] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  // Owner review modal state
  const [showOwnerReviewModal, setShowOwnerReviewModal] = useState(false);
  const [ownerReviewApproved, setOwnerReviewApproved] = useState(true);
  const [ownerReviewComment, setOwnerReviewComment] = useState('');
  const [ownerReviewSubmitting, setOwnerReviewSubmitting] = useState(false);
  const [ownerReviewAcknowledged, setOwnerReviewAcknowledged] = useState(false);
  const [ownerDateOverride, setOwnerDateOverride] = useState<string | null>(null);
  const [retirementCertified, setRetirementCertified] = useState(false);

  // Approval modal state
  const [approvalModal, setApprovalModal] = useState<Approval | null>(null);
  const [approvalDecision, setApprovalDecision] = useState(true);
  const [approvalComment, setApprovalComment] = useState('');
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);

  // Withdraw modal state
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState('');
  const [withdrawSubmitting, setWithdrawSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [modelId]);

  // Click outside handler for replacement model dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (replacementDropdownRef.current && !replacementDropdownRef.current.contains(event.target as Node)) {
        setShowReplacementDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    // Calculate gap when dates change
    if (replacementCurrentDate && lastProductionDate) {
      const implDate = new Date(replacementCurrentDate);
      const retireDate = new Date(lastProductionDate);
      const diffDays = Math.ceil((implDate.getTime() - retireDate.getTime()) / (1000 * 60 * 60 * 24));
      setGapDays(diffDays > 0 ? diffDays : null);
    } else if (replacementImplDate && lastProductionDate) {
      const implDate = new Date(replacementImplDate);
      const retireDate = new Date(lastProductionDate);
      const diffDays = Math.ceil((implDate.getTime() - retireDate.getTime()) / (1000 * 60 * 60 * 24));
      setGapDays(diffDays > 0 ? diffDays : null);
    } else {
      setGapDays(null);
    }
  }, [replacementCurrentDate, replacementImplDate, lastProductionDate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch model details
      const modelResponse = await api.get(`/models/${modelId}`);
      setModel(modelResponse.data);

      // Check for existing request
      const requestsResponse = await api.get(`/decommissioning/?model_id=${modelId}`);
      const activeRequest = requestsResponse.data.find(
        (r: DecommissioningRequest) => ['PENDING', 'VALIDATOR_APPROVED'].includes(r.status)
      );

      // Fetch downstream dependencies (consumers of this model)
      try {
        const depsResponse = await api.get(`/models/${modelId}/dependencies/outbound`);
        setDownstreamDependencies(depsResponse.data.filter((d: DownstreamDependency) => d.is_active));
      } catch {
        // Dependencies endpoint might not exist or model has none - that's fine
        setDownstreamDependencies([]);
      }

      if (activeRequest) {
        // Fetch full details
        const detailResponse = await api.get(`/decommissioning/${activeRequest.request_id}`);
        setExistingRequest(detailResponse.data);
        setFormMode('view');
      } else {
        setFormMode('create');
        // Fetch reasons taxonomy
        const taxResponse = await api.get('/taxonomies/');
        const reasonTax = taxResponse.data.find((t: any) => t.name === 'Model Decommission Reason');
        if (reasonTax) {
          // GET /taxonomies/{id} returns values nested in the response
          const taxDetailResponse = await api.get(`/taxonomies/${reasonTax.taxonomy_id}`);
          setReasons((taxDetailResponse.data.values || []).filter((v: any) => v.is_active));
        }

        // Fetch models for replacement selection
        const modelsResponse = await api.get('/models/?limit=1000');
        setAllModels(modelsResponse.data.items || modelsResponse.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const checkReplacementImplementationDate = async (replModelId: number) => {
    try {
      const response = await api.get(`/decommissioning/models/${replModelId}/implementation-date`);
      setReplacementHasDate(response.data.has_implementation_date);
      setReplacementCurrentDate(response.data.implementation_date);
    } catch {
      setReplacementHasDate(false);
      setReplacementCurrentDate(null);
    }
  };

  const selectReplacementModel = (selectedModel: ModelListItem) => {
    setReplacementModelId(selectedModel.model_id);
    setReplacementSearch(selectedModel.model_name);
    setShowReplacementDropdown(false);
    setReplacementImplDate('');
    setReplacementHasDate(null);
    setReplacementCurrentDate(null);
    checkReplacementImplementationDate(selectedModel.model_id);
  };

  const clearReplacementModel = () => {
    setReplacementModelId(null);
    setReplacementSearch('');
    setReplacementHasDate(null);
    setReplacementCurrentDate(null);
    setReplacementImplDate('');
  };

  // Filter models based on search query
  const filteredModels = allModels
    .filter(m => m.model_id !== modelId)
    .filter(m => {
      const normalizedSearch = replacementSearch.toLowerCase();
      return (
        m.model_name.toLowerCase().includes(normalizedSearch) ||
        String(m.model_id).includes(normalizedSearch)
      );
    });

  const selectedReason = reasons.find(r => r.value_id === reasonId);
  const requiresReplacement = selectedReason && REASONS_REQUIRING_REPLACEMENT.includes(selectedReason.code);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!reasonId) {
      alert('Please select a reason');
      return;
    }

    if (requiresReplacement && !replacementModelId) {
      alert('Selected reason requires a replacement model');
      return;
    }

    if (!downstreamVerified) {
      alert('You must verify downstream impact before submitting');
      return;
    }

    if (gapDays && gapDays > 0 && !gapJustification.trim()) {
      alert('Gap justification is required when there is a gap between retirement and replacement dates');
      return;
    }

    try {
      setSubmitting(true);

      const payload: any = {
        model_id: modelId,
        reason_id: reasonId,
        last_production_date: lastProductionDate,
        archive_location: archiveLocation,
        downstream_impact_verified: downstreamVerified,
      };

      if (replacementModelId) {
        payload.replacement_model_id = replacementModelId;
      }

      if (replacementModelId && !replacementHasDate && replacementImplDate) {
        payload.replacement_implementation_date = replacementImplDate;
      }

      if (gapJustification.trim()) {
        payload.gap_justification = gapJustification;
      }

      const response = await api.post('/decommissioning/', payload);
      setExistingRequest(response.data);
      setFormMode('view');

      // Link to attestation if navigated from attestation page
      if (response.data.request_id) {
        await linkChangeToAttestationIfPresent('DECOMMISSION', {
          model_id: modelId,
          decommissioning_request_id: response.data.request_id,
        });
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleValidatorReview = async () => {
    if (!reviewComment.trim()) {
      alert('Comment is required');
      return;
    }

    try {
      setReviewSubmitting(true);
      await api.post(`/decommissioning/${existingRequest?.request_id}/validator-review`, {
        approved: reviewApproved,
        comment: reviewComment,
      });
      setShowReviewModal(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setReviewSubmitting(false);
    }
  };

  const handleOwnerReview = async () => {
    try {
      setOwnerReviewSubmitting(true);
      await api.post(`/decommissioning/${existingRequest?.request_id}/owner-review`, {
        approved: ownerReviewApproved,
        comment: ownerReviewComment,
      });
      setShowOwnerReviewModal(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit owner review');
    } finally {
      setOwnerReviewSubmitting(false);
    }
  };

  const handleApprovalSubmit = async () => {
    if (!approvalModal) return;

    try {
      setApprovalSubmitting(true);
      await api.post(
        `/decommissioning/${existingRequest?.request_id}/approvals/${approvalModal.approval_id}`,
        {
          is_approved: approvalDecision,
          comment: approvalComment || null,
        }
      );
      setApprovalModal(null);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit approval');
    } finally {
      setApprovalSubmitting(false);
    }
  };

  const handleWithdraw = async () => {
    try {
      setWithdrawSubmitting(true);
      await api.post(`/decommissioning/${existingRequest?.request_id}/withdraw`, {
        reason: withdrawReason || null,
      });
      setShowWithdrawModal(false);
      navigate(`/models/${modelId}`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to withdraw request');
    } finally {
      setWithdrawSubmitting(false);
    }
  };

  // Validator can review if: status is PENDING, validator hasn't reviewed yet, and user is Admin/Validator
  const canValidatorReview = existingRequest?.status === 'PENDING' &&
    !existingRequest?.validator_reviewed_at &&
    (user?.role === 'Admin' || user?.role === 'Validator');

  // Owner can review if: owner_approval_required is true, status is PENDING, owner hasn't reviewed yet,
  // and current user is the model owner (or Admin)
  const canOwnerReview = existingRequest?.status === 'PENDING' &&
    existingRequest?.owner_approval_required &&
    !existingRequest?.owner_reviewed_at &&
    (user?.role === 'Admin' || user?.user_id === existingRequest?.model?.owner_id);

  const canApprove = (approval: Approval) => {
    if (existingRequest?.status !== 'VALIDATOR_APPROVED') return false;
    if (approval.is_approved !== null) return false;
    if (user?.role === 'Admin') return true;
    if (approval.approver_type === 'GLOBAL' && user?.role === 'Global Approver') return true;
    // Regional approvers would need region assignment check (simplified here)
    if (approval.approver_type === 'REGIONAL' && user?.role === 'Regional Approver') return true;
    return false;
  };

  const canWithdraw = existingRequest &&
    ['PENDING', 'VALIDATOR_APPROVED'].includes(existingRequest.status) &&
    (user?.role === 'Admin' || user?.user_id === existingRequest.created_by_id);

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      case 'VALIDATOR_APPROVED': return 'bg-blue-100 text-blue-800';
      case 'APPROVED': return 'bg-green-100 text-green-800';
      case 'REJECTED': return 'bg-red-100 text-red-800';
      case 'WITHDRAWN': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Helper to determine if the effective last production date is in the future
  const getEffectiveLastProductionDate = () => {
    return ownerDateOverride || existingRequest?.last_production_date;
  };

  const isLastProductionDateInFuture = () => {
    const effectiveDate = getEffectiveLastProductionDate();
    if (!effectiveDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const prodDate = new Date(effectiveDate);
    prodDate.setHours(0, 0, 0, 0);
    return prodDate > today;
  };

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-gray-500">Loading...</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button onClick={() => navigate(-1)} className="mt-2 text-blue-600 hover:underline">
            Go Back
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <Link to="/models" className="hover:text-blue-600">Models</Link>
              <span>/</span>
              <Link to={`/models/${modelId}`} className="hover:text-blue-600">{model?.model_name}</Link>
              <span>/</span>
              <span>Decommission</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">
              {formMode === 'create' ? 'Initiate Decommissioning' : 'Decommissioning Request'}
            </h1>
            <p className="mt-1 text-gray-600">
              Model: <strong>{model?.model_name}</strong>
            </p>
          </div>
          {existingRequest && (
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusBadgeColor(existingRequest.status)}`}>
              {existingRequest.status.replace('_', ' ')}
            </span>
          )}
        </div>

        {/* Create Form */}
        {formMode === 'create' && (
          <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Decommissioning Reason *
                </label>
                <select
                  value={reasonId || ''}
                  onChange={(e) => setReasonId(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select reason...</option>
                  {reasons.map((r) => (
                    <option key={r.value_id} value={r.value_id}>{r.label}</option>
                  ))}
                </select>
                {selectedReason && REASONS_REQUIRING_REPLACEMENT.includes(selectedReason.code) && (
                  <p className="text-sm text-amber-600 mt-1">
                    This reason requires selecting a replacement model.
                  </p>
                )}
              </div>

              {/* Last Production Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Production Date *
                </label>
                <input
                  type="date"
                  value={lastProductionDate}
                  onChange={(e) => setLastProductionDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  The date when this model will no longer be in production use.
                </p>
              </div>

              {/* Replacement Model */}
              <div ref={replacementDropdownRef} className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Replacement Model {requiresReplacement && '*'}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={replacementSearch}
                    onChange={(e) => {
                      setReplacementSearch(e.target.value);
                      setShowReplacementDropdown(true);
                      // If user clears the search, also clear the selection
                      if (!e.target.value) {
                        clearReplacementModel();
                      }
                    }}
                    onFocus={() => setShowReplacementDropdown(true)}
                    placeholder="Search by name or ID..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {replacementModelId && (
                    <button
                      type="button"
                      onClick={clearReplacementModel}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                {showReplacementDropdown && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                    <button
                      type="button"
                      onClick={() => {
                        clearReplacementModel();
                        setShowReplacementDropdown(false);
                      }}
                      className="w-full px-3 py-2 text-left text-gray-500 hover:bg-gray-100"
                    >
                      No replacement
                    </button>
                    {filteredModels.length === 0 ? (
                      <div className="px-3 py-2 text-gray-500 text-sm">
                        No models found
                      </div>
                    ) : (
                      filteredModels.slice(0, 50).map((m) => (
                        <button
                          key={m.model_id}
                          type="button"
                          onClick={() => selectReplacementModel(m)}
                          className={`w-full px-3 py-2 text-left hover:bg-blue-50 ${
                            replacementModelId === m.model_id ? 'bg-blue-100 text-blue-800' : ''
                          }`}
                        >
                          <div className="font-medium">{m.model_name}</div>
                          <div className="text-xs text-gray-500">ID: {m.model_id}</div>
                        </button>
                      ))
                    )}
                    {filteredModels.length > 50 && (
                      <div className="px-3 py-2 text-gray-400 text-xs text-center border-t">
                        Showing first 50 results. Type more to narrow search.
                      </div>
                    )}
                  </div>
                )}
                {requiresReplacement && !replacementModelId && (
                  <input type="hidden" required value="" />
                )}
                {replacementHasDate === true && replacementCurrentDate && (
                  <p className="text-sm text-green-600 mt-1">
                    Implementation date: {replacementCurrentDate}
                  </p>
                )}
                {replacementHasDate === false && (
                  <p className="text-sm text-amber-600 mt-1">
                    This model has no implementation date. Please provide one below.
                  </p>
                )}
              </div>

              {/* Replacement Implementation Date (if needed) */}
              {replacementModelId && replacementHasDate === false && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Replacement Implementation Date *
                  </label>
                  <input
                    type="date"
                    value={replacementImplDate}
                    onChange={(e) => setReplacementImplDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    A new version will be created for the replacement model with this date.
                  </p>
                </div>
              )}

              {/* Archive Location */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Archive Location *
                </label>
                <input
                  type="text"
                  value={archiveLocation}
                  onChange={(e) => setArchiveLocation(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., S3://archive/models/2024/model-123 or SharePoint URL"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Where model artifacts, documentation, and audit records will be archived.
                </p>
              </div>
            </div>

            {/* Gap Warning & Justification */}
            {gapDays && gapDays > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <h4 className="font-semibold text-amber-800 mb-2">
                  Gap Period Detected: {gapDays} days
                </h4>
                <p className="text-sm text-amber-700 mb-3">
                  The replacement model's implementation date is after the retirement date.
                  Please provide a justification for this coverage gap.
                </p>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Gap Justification *
                </label>
                <textarea
                  value={gapJustification}
                  onChange={(e) => setGapJustification(e.target.value)}
                  className="w-full px-3 py-2 border border-amber-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500"
                  rows={3}
                  placeholder="Explain how the business will operate during this gap period..."
                  required
                />
              </div>
            )}

            {/* Downstream Impact Verification */}
            <div className="space-y-3">
              {/* Warning if model has downstream consumers */}
              {downstreamDependencies.length > 0 && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="h-6 w-6 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div className="flex-1">
                      <h4 className="font-semibold text-amber-800">
                        This model has {downstreamDependencies.length} downstream consumer{downstreamDependencies.length !== 1 ? 's' : ''}
                      </h4>
                      <p className="text-sm text-amber-700 mt-1">
                        The following models depend on data from this model. Decommissioning may disrupt their operations:
                      </p>
                      <ul className="mt-2 space-y-1">
                        {downstreamDependencies.map((dep) => (
                          <li key={dep.id} className="text-sm">
                            <Link
                              to={`/models/${dep.model_id}`}
                              className="text-amber-800 hover:text-amber-900 font-medium hover:underline"
                              target="_blank"
                            >
                              {dep.model_name}
                            </Link>
                            <span className="text-amber-600 ml-2">
                              ({dep.dependency_type})
                            </span>
                          </li>
                        ))}
                      </ul>
                      <p className="text-sm text-amber-700 mt-3 font-medium">
                        Please ensure you have notified the owners of these models before proceeding.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Confirmation checkbox */}
              <div className={`border rounded-lg p-4 ${downstreamDependencies.length > 0 ? 'bg-amber-50 border-amber-200' : 'bg-gray-50 border-gray-200'}`}>
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={downstreamVerified}
                    onChange={(e) => setDownstreamVerified(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <div>
                    <span className="font-medium text-gray-700">
                      I confirm that I have verified downstream impact *
                    </span>
                    <p className="text-sm text-gray-500 mt-1">
                      {downstreamDependencies.length > 0
                        ? `By checking this box, you confirm that you have reviewed the ${downstreamDependencies.length} downstream consumer${downstreamDependencies.length !== 1 ? 's' : ''} listed above, notified affected parties, and verified that decommissioning this model will not cause unexpected disruptions.`
                        : 'By checking this box, you confirm that you have reviewed all downstream consumers, notified affected parties, and verified that decommissioning this model will not cause unexpected disruptions.'}
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Submit */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => navigate(`/models/${modelId}`)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400"
              >
                {submitting ? 'Submitting...' : 'Submit Decommissioning Request'}
              </button>
            </div>
          </form>
        )}

        {/* View Existing Request */}
        {formMode === 'view' && existingRequest && (
          <div className="space-y-6">
            {/* Request Details */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Request Details</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-gray-500">Request ID</span>
                  <p className="font-medium">{existingRequest.request_id}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Status</span>
                  <p>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusBadgeColor(existingRequest.status)}`}>
                      {existingRequest.status.replace('_', ' ')}
                    </span>
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Reason</span>
                  <p className="font-medium">{existingRequest.reason?.label || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Last Production Date</span>
                  <p className="font-medium">{existingRequest.last_production_date}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Replacement Model</span>
                  <p className="font-medium">
                    {existingRequest.replacement_model ? (
                      <Link to={`/models/${existingRequest.replacement_model.model_id}`} className="text-blue-600 hover:underline">
                        {existingRequest.replacement_model.model_name}
                      </Link>
                    ) : (
                      <span className="text-gray-400">None</span>
                    )}
                  </p>
                </div>
                {existingRequest.gap_days && existingRequest.gap_days > 0 && (
                  <div>
                    <span className="text-sm text-gray-500">Gap Period</span>
                    <p className="font-medium text-amber-600">{existingRequest.gap_days} days</p>
                  </div>
                )}
                <div className="md:col-span-2">
                  <span className="text-sm text-gray-500">Archive Location</span>
                  <p className="font-medium">{existingRequest.archive_location}</p>
                </div>
                {existingRequest.gap_justification && (
                  <div className="md:col-span-2">
                    <span className="text-sm text-gray-500">Gap Justification</span>
                    <p className="font-medium">{existingRequest.gap_justification}</p>
                  </div>
                )}
                <div>
                  <span className="text-sm text-gray-500">Created By</span>
                  <p className="font-medium">{existingRequest.created_by?.full_name || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Created At</span>
                  <p className="font-medium">{existingRequest.created_at.split('T')[0]}</p>
                </div>
              </div>
            </div>

            {/* Stage 1 Reviews Section (Validator + Owner if required) */}
            {(existingRequest.validator_reviewed_at || existingRequest.owner_approval_required) && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Stage 1 Reviews</h2>

                {/* Pending Reviews Indicator */}
                {existingRequest.status === 'PENDING' && (
                  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-sm text-yellow-700">
                      <strong>Pending:</strong>{' '}
                      {!existingRequest.validator_reviewed_at && 'Validator Review'}
                      {!existingRequest.validator_reviewed_at && existingRequest.owner_approval_required && !existingRequest.owner_reviewed_at && ', '}
                      {existingRequest.owner_approval_required && !existingRequest.owner_reviewed_at && 'Model Owner Review'}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Validator Review */}
                  <div className={`p-4 rounded-lg ${existingRequest.validator_reviewed_at ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                    <h3 className="font-semibold mb-3 flex items-center gap-2">
                      Validator Review
                      {existingRequest.validator_reviewed_at && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">Completed</span>
                      )}
                      {!existingRequest.validator_reviewed_at && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">Pending</span>
                      )}
                    </h3>
                    {existingRequest.validator_reviewed_at ? (
                      <div className="space-y-2 text-sm">
                        <p><span className="text-gray-500">Reviewed By:</span> {existingRequest.validator_reviewed_by?.full_name || '-'}</p>
                        <p><span className="text-gray-500">Date:</span> {existingRequest.validator_reviewed_at.split('T')[0]}</p>
                        <p><span className="text-gray-500">Comment:</span> {existingRequest.validator_comment || '-'}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500">Awaiting validator review</p>
                    )}
                  </div>

                  {/* Owner Review (only if required) */}
                  {existingRequest.owner_approval_required && (
                    <div className={`p-4 rounded-lg ${existingRequest.owner_reviewed_at ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                      <h3 className="font-semibold mb-3 flex items-center gap-2">
                        Model Owner Review
                        {existingRequest.owner_reviewed_at && (
                          <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">Completed</span>
                        )}
                        {!existingRequest.owner_reviewed_at && (
                          <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">Pending</span>
                        )}
                      </h3>
                      {existingRequest.owner_reviewed_at ? (
                        <div className="space-y-2 text-sm">
                          <p><span className="text-gray-500">Reviewed By:</span> {existingRequest.owner_reviewed_by?.full_name || '-'}</p>
                          <p><span className="text-gray-500">Date:</span> {existingRequest.owner_reviewed_at.split('T')[0]}</p>
                          <p><span className="text-gray-500">Comment:</span> {existingRequest.owner_comment || '-'}</p>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">Awaiting model owner review</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Note about dual approval requirement */}
                {existingRequest.owner_approval_required && existingRequest.status === 'PENDING' && (
                  <p className="mt-4 text-xs text-gray-500 italic">
                    Note: Both Validator and Model Owner must approve before proceeding to Stage 2 (Global/Regional approvals).
                  </p>
                )}
              </div>
            )}

            {/* Approvals Section */}
            {existingRequest.approvals.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Approvals</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Approved By</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {existingRequest.approvals.map((approval) => (
                        <tr key={approval.approval_id}>
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                            {approval.approver_type}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {approval.region?.name || '-'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            {approval.is_approved === null && (
                              <span className="px-2 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800">Pending</span>
                            )}
                            {approval.is_approved === true && (
                              <span className="px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">Approved</span>
                            )}
                            {approval.is_approved === false && (
                              <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">Rejected</span>
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {approval.approved_by?.full_name || '-'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {approval.approved_at?.split('T')[0] || '-'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {canApprove(approval) && (
                              <button
                                onClick={() => {
                                  setApprovalModal(approval);
                                  setApprovalDecision(true);
                                  setApprovalComment('');
                                }}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                Review
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Status History */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Status History</h2>
              <div className="space-y-3">
                {existingRequest.status_history.map((h) => (
                  <div key={h.history_id} className="flex items-start gap-4 p-3 bg-gray-50 rounded">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {h.old_status && (
                          <>
                            <span className="text-gray-500">{h.old_status.replace('_', ' ')}</span>
                            <span className="text-gray-400">→</span>
                          </>
                        )}
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusBadgeColor(h.new_status)}`}>
                          {h.new_status.replace('_', ' ')}
                        </span>
                      </div>
                      {h.notes && <p className="text-sm text-gray-600 mt-1">{h.notes}</p>}
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      <p>{h.changed_by?.full_name}</p>
                      <p>{h.changed_at.split('T')[0]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Rejection Reason */}
            {existingRequest.status === 'REJECTED' && existingRequest.rejection_reason && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="font-semibold text-red-800 mb-2">Rejection Reason</h3>
                <p className="text-red-700">{existingRequest.rejection_reason}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => navigate(`/models/${modelId}`)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Back to Model
              </button>

              {canValidatorReview && (
                <button
                  onClick={() => {
                    setShowReviewModal(true);
                    setReviewApproved(true);
                    setReviewComment('');
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Submit Validator Review
                </button>
              )}

              {canOwnerReview && (
                <button
                  onClick={() => {
                    setShowOwnerReviewModal(true);
                    setOwnerReviewApproved(true);
                    setOwnerReviewComment('');
                    setOwnerReviewAcknowledged(false);
                    setOwnerDateOverride(null);
                    setRetirementCertified(false);
                  }}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                >
                  Submit Owner Review
                </button>
              )}

              {canWithdraw && (
                <button
                  onClick={() => {
                    setShowWithdrawModal(true);
                    setWithdrawReason('');
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  Withdraw Request
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Validator Review Modal */}
      {showReviewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
            <h2 className="text-2xl font-bold mb-4">Validator Review</h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Decision</label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={reviewApproved}
                    onChange={() => setReviewApproved(true)}
                    className="mr-2"
                  />
                  Approve
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={!reviewApproved}
                    onChange={() => setReviewApproved(false)}
                    className="mr-2"
                  />
                  Reject
                </label>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Comment *
              </label>
              <textarea
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                placeholder="Provide your review comments..."
                required
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowReviewModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={reviewSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleValidatorReview}
                disabled={reviewSubmitting || !reviewComment.trim()}
                className={`px-4 py-2 text-white rounded-md ${reviewApproved ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'} disabled:bg-gray-400`}
              >
                {reviewSubmitting ? 'Submitting...' : reviewApproved ? 'Approve' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Owner Review Modal */}
      {showOwnerReviewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Model Owner Review</h2>

            <p className="text-gray-600 mb-4">
              As the model owner, please review this decommissioning request.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Decision</label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={ownerReviewApproved}
                    onChange={() => {
                      setOwnerReviewApproved(true);
                      setOwnerReviewAcknowledged(false);
                      setOwnerDateOverride(null);
                      setRetirementCertified(false);
                    }}
                    className="mr-2"
                  />
                  Approve
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={!ownerReviewApproved}
                    onChange={() => {
                      setOwnerReviewApproved(false);
                      setOwnerReviewAcknowledged(false);
                      setOwnerDateOverride(null);
                      setRetirementCertified(false);
                    }}
                    className="mr-2"
                  />
                  Reject
                </label>
              </div>
            </div>

            {/* Assertion language and date handling for approval */}
            {ownerReviewApproved && (
              <>
                {/* Last Production Date handling */}
                <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-gray-600">
                      <strong>Last Production Date:</strong> {getEffectiveLastProductionDate()}
                      {ownerDateOverride && (
                        <span className="ml-2 text-amber-600">(overridden from {existingRequest?.last_production_date})</span>
                      )}
                    </p>
                    {ownerDateOverride && (
                      <button
                        type="button"
                        onClick={() => setOwnerDateOverride(null)}
                        className="px-2 py-1 text-xs font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 rounded transition-colors"
                      >
                        Reset to Original
                      </button>
                    )}
                  </div>

                  {/* Future date warning and override option */}
                  {isLastProductionDateInFuture() && (
                    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded">
                      <div className="flex items-start gap-2 mb-2">
                        <svg className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <div>
                          <p className="text-sm text-amber-800 font-medium">
                            The last production date is in the future.
                          </p>
                          <p className="text-sm text-amber-700 mt-1">
                            By approving now, you authorize the planned decommissioning. You will need to return and certify the final retirement once the model has been deactivated on or after the last production date.
                          </p>
                        </div>
                      </div>
                      <div className="mt-3">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Override Last Production Date (optional)
                        </label>
                        <input
                          type="date"
                          value={ownerDateOverride || ''}
                          onChange={(e) => setOwnerDateOverride(e.target.value || null)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500 text-sm"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          If the proposed date is incorrect, you may override it here.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Past/today date - retirement certification */}
                  {!isLastProductionDateInFuture() && (
                    <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
                      <label className="flex items-start gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={retirementCertified}
                          onChange={(e) => setRetirementCertified(e.target.checked)}
                          className="mt-0.5"
                        />
                        <div>
                          <span className="text-sm text-green-800 font-medium">
                            I certify that this model has been retired and is no longer in use *
                          </span>
                          <p className="text-xs text-green-700 mt-1">
                            By checking this box, you confirm that the model has been deactivated in production and is no longer processing transactions or generating outputs.
                          </p>
                        </div>
                      </label>
                    </div>
                  )}
                </div>

                {/* General approval certifications */}
                <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-md">
                  <p className="text-sm text-purple-800 font-medium mb-2">
                    By approving this request, I certify that:
                  </p>
                  <ul className="text-sm text-purple-700 list-disc list-inside space-y-1 mb-3">
                    <li>I have reviewed the decommissioning rationale and agree the model should be retired</li>
                    <li>I understand the downstream impacts have been assessed and consumers notified</li>
                    <li>I concur with the proposed last production date and any gap analysis provided</li>
                    <li>I acknowledge this model will no longer be available for use after retirement</li>
                  </ul>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ownerReviewAcknowledged}
                      onChange={(e) => setOwnerReviewAcknowledged(e.target.checked)}
                      className="mt-0.5"
                    />
                    <span className="text-sm text-purple-800 font-medium">
                      I acknowledge and accept these certifications *
                    </span>
                  </label>
                </div>
              </>
            )}

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Comment (optional)
              </label>
              <textarea
                value={ownerReviewComment}
                onChange={(e) => setOwnerReviewComment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={2}
                placeholder={ownerReviewApproved
                  ? "Provide any additional comments regarding your approval..."
                  : "Please explain the reason for rejection..."
                }
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowOwnerReviewModal(false);
                  setOwnerReviewAcknowledged(false);
                  setOwnerDateOverride(null);
                  setRetirementCertified(false);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={ownerReviewSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleOwnerReview}
                disabled={
                  ownerReviewSubmitting ||
                  (ownerReviewApproved && !ownerReviewAcknowledged) ||
                  (ownerReviewApproved && !isLastProductionDateInFuture() && !retirementCertified)
                }
                className={`px-4 py-2 text-white rounded-md ${ownerReviewApproved ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'} disabled:bg-gray-400`}
              >
                {ownerReviewSubmitting ? 'Submitting...' : ownerReviewApproved ? 'Approve' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Approval Modal */}
      {approvalModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
            <h2 className="text-2xl font-bold mb-4">
              {approvalModal.approver_type} Approval
              {approvalModal.region && ` - ${approvalModal.region.name}`}
            </h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Decision</label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={approvalDecision}
                    onChange={() => setApprovalDecision(true)}
                    className="mr-2"
                  />
                  Approve
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={!approvalDecision}
                    onChange={() => setApprovalDecision(false)}
                    className="mr-2"
                  />
                  Reject
                </label>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Comment
              </label>
              <textarea
                value={approvalComment}
                onChange={(e) => setApprovalComment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                placeholder="Optional comment..."
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setApprovalModal(null)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={approvalSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleApprovalSubmit}
                disabled={approvalSubmitting}
                className={`px-4 py-2 text-white rounded-md ${approvalDecision ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'} disabled:bg-gray-400`}
              >
                {approvalSubmitting ? 'Submitting...' : approvalDecision ? 'Approve' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
            <h2 className="text-2xl font-bold mb-4">Withdraw Request</h2>

            <p className="text-gray-600 mb-4">
              Are you sure you want to withdraw this decommissioning request?
              The model will return to Active status.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason (optional)
              </label>
              <textarea
                value={withdrawReason}
                onChange={(e) => setWithdrawReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Why are you withdrawing this request?"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowWithdrawModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={withdrawSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleWithdraw}
                disabled={withdrawSubmitting}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:bg-gray-400"
              >
                {withdrawSubmitting ? 'Withdrawing...' : 'Withdraw Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default DecommissioningRequestPage;

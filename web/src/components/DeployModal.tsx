/**
 * DeployModal - Modal for deploying a version to one or more regions.
 *
 * Features:
 * - Radio toggle: "Deploy Now" vs "Schedule for Later"
 * - Region checklist with current deployment status
 * - Lock icon for regions requiring regional approval (not in validation scope)
 * - Single date for Deploy Now, per-region dates for Schedule for Later
 * - Select All / Clear buttons
 * - Smart button text showing count
 */
import React, { useState, useEffect } from 'react';
import { deploymentsApi, DeployModalData, RegionDeploymentStatus } from '../api/deployments';

interface DeployModalProps {
    versionId: number;
    onClose: () => void;
    onSuccess: () => void;
}

const DeployModal: React.FC<DeployModalProps> = ({ versionId, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [modalData, setModalData] = useState<DeployModalData | null>(null);

    // Form state
    const [deployMode, setDeployMode] = useState<'now' | 'later'>('now');
    const [selectedRegions, setSelectedRegions] = useState<Set<number>>(new Set());
    const [deployDate, setDeployDate] = useState(getTodayISO());
    const [regionDates, setRegionDates] = useState<Map<number, string>>(new Map());
    const [notes, setNotes] = useState('');
    const [validationOverrideReason, setValidationOverrideReason] = useState('');

    function getTodayISO(): string {
        return new Date().toISOString().split('T')[0];
    }

    // Fetch modal data
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await deploymentsApi.getDeployModalData(versionId);
                setModalData(response.data);

                // Pre-select regions that don't have pending tasks
                const preSelect = new Set<number>();
                const dates = new Map<number, string>();
                response.data.regions.forEach((r: RegionDeploymentStatus) => {
                    if (!r.has_pending_task) {
                        preSelect.add(r.region_id);
                    }
                    dates.set(r.region_id, getTodayISO());
                });
                setSelectedRegions(preSelect);
                setRegionDates(dates);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load deployment data');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [versionId]);

    const handleSelectAll = () => {
        if (!modalData) return;
        const all = new Set<number>();
        modalData.regions.forEach(r => {
            if (!r.has_pending_task) {
                all.add(r.region_id);
            }
        });
        setSelectedRegions(all);
    };

    const handleClearSelection = () => {
        setSelectedRegions(new Set());
    };

    const handleRegionToggle = (regionId: number) => {
        const region = modalData?.regions.find(r => r.region_id === regionId);
        if (region?.has_pending_task) return; // Can't select regions with pending tasks

        const newSet = new Set(selectedRegions);
        if (newSet.has(regionId)) {
            newSet.delete(regionId);
        } else {
            newSet.add(regionId);
        }
        setSelectedRegions(newSet);
    };

    const handleRegionDateChange = (regionId: number, date: string) => {
        const newDates = new Map(regionDates);
        newDates.set(regionId, date);
        setRegionDates(newDates);
    };

    const handleApplySameDateToAll = () => {
        const newDates = new Map<number, string>();
        selectedRegions.forEach(regionId => {
            newDates.set(regionId, deployDate);
        });
        setRegionDates(newDates);
    };

    const handleSubmit = async () => {
        if (selectedRegions.size === 0) {
            setError('Please select at least one region');
            return;
        }

        // Issue 4 fix: Validation override only required for Deploy Now mode
        // Scheduling for later doesn't require override since validation may complete before deployment
        if (deployMode === 'now' && !modalData?.validation_approved && !validationOverrideReason.trim()) {
            setError('Validation is not approved. Please provide a reason for immediate deployment without approval.');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const deployments = Array.from(selectedRegions).map(regionId => ({
                region_id: regionId,
                production_date: deployMode === 'now' ? deployDate : (regionDates.get(regionId) || deployDate),
                notes: notes || undefined,
            }));

            await deploymentsApi.deployVersion(versionId, {
                deployments,
                deploy_now: deployMode === 'now',
                validation_override_reason: modalData?.validation_approved ? undefined : validationOverrideReason,
                shared_notes: notes || undefined,
            });

            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to deploy version');
        } finally {
            setSubmitting(false);
        }
    };

    // Get regions that will require regional approval (show lock icon)
    const getRegionsRequiringApproval = (): string[] => {
        if (!modalData) return [];
        return modalData.regions
            .filter(r => r.requires_regional_approval && selectedRegions.has(r.region_id))
            .map(r => r.region_code);
    };

    const regionsRequiringApproval = getRegionsRequiringApproval();
    const selectedCount = selectedRegions.size;

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl">
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span className="ml-3 text-gray-600">Loading deployment data...</span>
                    </div>
                </div>
            </div>
        );
    }

    if (!modalData) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl">
                    <div className="text-red-600">Failed to load deployment data</div>
                    <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-600 text-white rounded">
                        Close
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Deploy Version {modalData.version_number}</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-2xl"
                    >
                        ✕
                    </button>
                </div>

                {/* Model & Version Info */}
                <div className="mb-4 pb-4 border-b">
                    <p className="text-lg font-medium text-gray-800">
                        {modalData.model_name} › v{modalData.version_number}
                    </p>
                    {modalData.change_description && (
                        <p className="text-gray-600 text-sm mt-1">"{modalData.change_description}"</p>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                        {modalData.validation_approved ? (
                            <span className="inline-flex items-center px-2 py-1 rounded text-sm bg-green-100 text-green-800">
                                ✓ Validation Approved
                                {modalData.validation_request_id && (
                                    <span className="ml-1 text-green-600">(VR-{modalData.validation_request_id})</span>
                                )}
                            </span>
                        ) : modalData.validation_status ? (
                            <span className="inline-flex items-center px-2 py-1 rounded text-sm bg-yellow-100 text-yellow-800">
                                ⚠ Validation: {modalData.validation_status}
                            </span>
                        ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded text-sm bg-gray-100 text-gray-600">
                                No validation attached
                            </span>
                        )}
                    </div>
                </div>

                {/* Error Display */}
                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                        {error}
                    </div>
                )}

                {/* Validation Override Warning */}
                {!modalData.validation_approved && (
                    <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded">
                        <p className="text-yellow-800 font-medium mb-2">
                            ⚠ Validation not approved
                        </p>
                        {deployMode === 'now' ? (
                            <>
                                <p className="text-sm text-yellow-700 mb-2">
                                    Deploying immediately without validation approval will create a Type 3 exception.
                                </p>
                                <label className="block text-sm font-medium text-yellow-800 mb-1">
                                    Override Reason (Required)
                                </label>
                                <textarea
                                    value={validationOverrideReason}
                                    onChange={(e) => setValidationOverrideReason(e.target.value)}
                                    className="w-full px-3 py-2 border border-yellow-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
                                    rows={2}
                                    placeholder="Explain why you are deploying without validation approval..."
                                />
                            </>
                        ) : (
                            <p className="text-sm text-yellow-700">
                                Scheduling deployment. Validation should be completed before the planned deployment date.
                            </p>
                        )}
                    </div>
                )}

                {/* Deploy Mode Toggle */}
                <div className="mb-4">
                    <div className="flex gap-6">
                        <label className="flex items-center cursor-pointer">
                            <input
                                type="radio"
                                name="deployMode"
                                value="now"
                                checked={deployMode === 'now'}
                                onChange={() => setDeployMode('now')}
                                className="w-4 h-4 text-blue-600"
                            />
                            <span className="ml-2 font-medium">Deploy Now</span>
                        </label>
                        <label className="flex items-center cursor-pointer">
                            <input
                                type="radio"
                                name="deployMode"
                                value="later"
                                checked={deployMode === 'later'}
                                onChange={() => setDeployMode('later')}
                                className="w-4 h-4 text-blue-600"
                            />
                            <span className="ml-2 font-medium">Schedule for Later</span>
                        </label>
                    </div>
                </div>

                {/* Region Selection */}
                <div className="mb-4">
                    <div className="flex justify-between items-center mb-2">
                        <label className="block text-sm font-medium text-gray-700">
                            Select Regions
                        </label>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={handleSelectAll}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Select All
                            </button>
                            <span className="text-gray-400">|</span>
                            <button
                                type="button"
                                onClick={handleClearSelection}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Clear
                            </button>
                        </div>
                    </div>

                    <div className="border rounded-lg divide-y max-h-64 overflow-y-auto">
                        {modalData.regions.map((region) => {
                            const isSelected = selectedRegions.has(region.region_id);
                            const isDisabled = region.has_pending_task;

                            return (
                                <div
                                    key={region.region_id}
                                    className={`flex items-center p-3 ${isDisabled ? 'bg-gray-50' : 'hover:bg-gray-50'}`}
                                >
                                    {/* Checkbox */}
                                    <input
                                        type="checkbox"
                                        checked={isSelected}
                                        disabled={isDisabled}
                                        onChange={() => handleRegionToggle(region.region_id)}
                                        className="w-4 h-4 text-blue-600 rounded disabled:opacity-50"
                                    />

                                    {/* Region Info */}
                                    <div className="ml-3 flex-grow">
                                        <div className="flex items-center gap-2">
                                            <span className={`font-medium ${isDisabled ? 'text-gray-400' : ''}`}>
                                                {region.region_code}
                                            </span>
                                            {region.requires_regional_approval && (
                                                <span title="Regional approval required (not in validation scope)">
                                                    🔒
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            {region.current_version_number ? (
                                                <>
                                                    Currently: v{region.current_version_number}
                                                    {region.deployed_at && (
                                                        <> • Deployed {region.deployed_at.split('T')[0]}</>
                                                    )}
                                                </>
                                            ) : (
                                                'Not deployed'
                                            )}
                                        </div>
                                        {region.has_pending_task && (
                                            <div className="text-sm text-yellow-600">
                                                Pending deployment task (planned: {region.pending_task_planned_date})
                                            </div>
                                        )}
                                    </div>

                                    {/* Per-region date (Schedule for Later mode) */}
                                    {deployMode === 'later' && isSelected && !isDisabled && (
                                        <input
                                            type="date"
                                            value={regionDates.get(region.region_id) || deployDate}
                                            onChange={(e) => handleRegionDateChange(region.region_id, e.target.value)}
                                            className="ml-2 px-2 py-1 border rounded text-sm"
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Deployment Date (Deploy Now mode) */}
                {deployMode === 'now' && (
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Deployment Date
                        </label>
                        <input
                            type="date"
                            value={deployDate}
                            onChange={(e) => setDeployDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                )}

                {/* Apply Same Date button (Schedule for Later mode) */}
                {deployMode === 'later' && selectedCount > 0 && (
                    <div className="mb-4 flex items-center gap-3">
                        <input
                            type="date"
                            value={deployDate}
                            onChange={(e) => setDeployDate(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                            type="button"
                            onClick={handleApplySameDateToAll}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            Apply to all selected
                        </button>
                    </div>
                )}

                {/* Notes */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Notes (optional)
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={2}
                        placeholder="e.g., Production release per Q1 schedule..."
                    />
                </div>

                {/* Regional Approval Notice - Issue 7 fix: Always show lock icon explanation */}
                <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600">
                    <p className="flex items-center gap-1">
                        <span className="text-yellow-500">🔒</span>
                        <strong>Lock icon</strong> indicates regions requiring separate regional approval
                        (not covered by validation scope).
                    </p>
                    {regionsRequiringApproval.length > 0 && (
                        <p className="mt-2 text-yellow-700">
                            <strong>{regionsRequiringApproval.length} region(s)</strong> selected will
                            trigger regional approval requests upon deployment: {regionsRequiringApproval.join(', ')}
                        </p>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                        disabled={submitting}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                        disabled={submitting || selectedCount === 0}
                    >
                        {submitting
                            ? 'Processing...'
                            : deployMode === 'now'
                            ? `Deploy to ${selectedCount} Region${selectedCount !== 1 ? 's' : ''}`
                            : `Schedule ${selectedCount} Deployment${selectedCount !== 1 ? 's' : ''}`}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DeployModal;

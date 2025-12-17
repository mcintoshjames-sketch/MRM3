import React, { useEffect, useState } from 'react';
import { deploymentsApi, RegionDeploymentStatus } from '../api/deployments';

interface VersionDeploymentStatusProps {
    versionId: number;
    versionNumber: string;
    refreshTrigger?: number;
}

/**
 * Shows deployment status across all regions for a specific version.
 * Status legend:
 * - 🟢 Deployed - Live in production
 * - 🟡 Pending - Scheduled, awaiting confirmation
 * - 🔴 Overdue - Past planned date
 * - ⚪ Not Started - No deployment scheduled
 * - 🔒 Requires Approval - Regional approval needed (not in validation scope)
 */
const VersionDeploymentStatus: React.FC<VersionDeploymentStatusProps> = ({
    versionId,
    versionNumber,
    refreshTrigger
}) => {
    const [regions, setRegions] = useState<RegionDeploymentStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [validationApproved, setValidationApproved] = useState(false);

    useEffect(() => {
        const fetchDeploymentStatus = async () => {
            try {
                setLoading(true);
                setError(null);
                const response = await deploymentsApi.getDeployModalData(versionId);
                setRegions(response.data.regions);
                setValidationApproved(response.data.validation_approved);
            } catch (err: any) {
                console.error('Failed to fetch deployment status:', err);
                setError(err.response?.data?.detail || 'Failed to load deployment status');
            } finally {
                setLoading(false);
            }
        };

        fetchDeploymentStatus();
    }, [versionId, refreshTrigger]);

    const getStatusInfo = (region: RegionDeploymentStatus) => {
        const isDeployedWithThisVersion = region.current_version_id === versionId;

        if (isDeployedWithThisVersion && region.deployed_at) {
            return {
                icon: '🟢',
                label: 'Deployed',
                color: 'text-green-600',
                bgColor: 'bg-green-100'
            };
        }

        if (region.has_pending_task) {
            // Check if overdue (planned date is in the past)
            if (region.pending_task_planned_date) {
                const plannedDate = new Date(region.pending_task_planned_date);
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                if (plannedDate < today) {
                    return {
                        icon: '🔴',
                        label: 'Overdue',
                        color: 'text-red-600',
                        bgColor: 'bg-red-100'
                    };
                }
            }
            return {
                icon: '🟡',
                label: 'Pending',
                color: 'text-yellow-600',
                bgColor: 'bg-yellow-100'
            };
        }

        return {
            icon: '⚪',
            label: 'Not Started',
            color: 'text-gray-500',
            bgColor: 'bg-gray-100'
        };
    };

    const formatDate = (dateString: string | null): string => {
        if (!dateString) return '-';
        return dateString.split('T')[0];
    };

    if (loading) {
        return (
            <div className="p-4 text-gray-500 text-sm">
                Loading deployment status...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-red-600 text-sm">
                {error}
            </div>
        );
    }

    if (regions.length === 0) {
        return (
            <div className="p-4 text-gray-500 text-sm">
                No regions configured for deployment.
            </div>
        );
    }

    return (
        <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
                Regional Deployment Status for v{versionNumber}
            </h4>
            <div className="overflow-hidden border border-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                Region
                            </th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                Status
                            </th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                Deployed / Planned
                            </th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                Validation
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {regions.map((region) => {
                            const statusInfo = getStatusInfo(region);
                            const isDeployedWithThisVersion = region.current_version_id === versionId;

                            return (
                                <tr key={region.region_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-2 text-sm font-medium text-gray-900">
                                        <div className="flex items-center gap-2">
                                            {region.region_name}
                                            <span className="text-xs text-gray-500">
                                                ({region.region_code})
                                            </span>
                                        </div>
                                        {region.current_version_number && !isDeployedWithThisVersion && (
                                            <div className="text-xs text-gray-500">
                                                Currently: v{region.current_version_number}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-sm">
                                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusInfo.bgColor} ${statusInfo.color}`}>
                                            <span>{statusInfo.icon}</span>
                                            {statusInfo.label}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2 text-sm text-gray-600">
                                        {isDeployedWithThisVersion && region.deployed_at ? (
                                            <span className="text-green-600 font-medium">
                                                {formatDate(region.deployed_at)}
                                            </span>
                                        ) : region.has_pending_task && region.pending_task_planned_date ? (
                                            <span className="text-yellow-600">
                                                Planned: {formatDate(region.pending_task_planned_date)}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">-</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-sm">
                                        <div className="flex items-center gap-2">
                                            {validationApproved ? (
                                                <span className="text-green-600 text-xs font-medium">
                                                    ✓ Approved
                                                </span>
                                            ) : (
                                                <span className="text-gray-500 text-xs">
                                                    Not Approved
                                                </span>
                                            )}
                                            {region.requires_regional_approval && !region.in_validation_scope && (
                                                <span
                                                    className="text-yellow-500"
                                                    title="Regional approval required (not in validation scope)"
                                                >
                                                    🔒
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Status Legend */}
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
                <span>
                    <span className="text-green-600">🟢</span> Deployed
                </span>
                <span>
                    <span className="text-yellow-600">🟡</span> Pending
                </span>
                <span>
                    <span className="text-red-600">🔴</span> Overdue
                </span>
                <span>
                    <span className="text-gray-400">⚪</span> Not Started
                </span>
                <span>
                    <span className="text-yellow-500">🔒</span> Requires Approval
                </span>
            </div>
        </div>
    );
};

export default VersionDeploymentStatus;

import React, { useState, useEffect } from 'react';
import { versionsApi, ModelVersion, VersionStatus } from '../api/versions';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';

interface VersionsListProps {
    modelId: number;
    refreshTrigger?: number;
    onVersionClick?: (version: ModelVersion) => void;
}

const VersionsList: React.FC<VersionsListProps> = ({ modelId, refreshTrigger, onVersionClick }) => {
    const { user } = useAuth();
    const [versions, setVersions] = useState<ModelVersion[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [exportingCSV, setExportingCSV] = useState(false);

    const loadVersions = async () => {
        try {
            setLoading(true);
            const data = await versionsApi.listVersions(modelId);
            setVersions(data);
            setError(null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load versions');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadVersions();
    }, [modelId, refreshTrigger]);

    const handleApprove = async (e: React.MouseEvent, versionId: number) => {
        e.stopPropagation(); // Prevent row click
        if (!confirm('Approve this version?')) return;
        try {
            await versionsApi.approveVersion(versionId);
            loadVersions();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to approve version');
        }
    };

    const handleActivate = async (e: React.MouseEvent, versionId: number) => {
        e.stopPropagation(); // Prevent row click
        if (!confirm('Activate this version? This will supersede the current active version.')) return;
        try {
            await versionsApi.activateVersion(versionId);
            loadVersions();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to activate version');
        }
    };

    const handleDelete = async (e: React.MouseEvent, versionId: number) => {
        e.stopPropagation(); // Prevent row click
        if (!confirm('Delete this draft version?')) return;
        try {
            await versionsApi.deleteVersion(versionId);
            loadVersions();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete version');
        }
    };

    const getStatusBadge = (status: VersionStatus) => {
        const colors = {
            DRAFT: 'bg-gray-200 text-gray-800',
            IN_VALIDATION: 'bg-blue-200 text-blue-800',
            APPROVED: 'bg-green-200 text-green-800',
            ACTIVE: 'bg-green-600 text-white',
            SUPERSEDED: 'bg-gray-400 text-gray-700',
        };
        return (
            <span className={`px-2 py-1 rounded text-xs font-semibold ${colors[status]}`}>
                {status}
            </span>
        );
    };

    const getChangeTypeBadge = (changeType: string) => {
        const isMajor = changeType === 'MAJOR';
        return (
            <span className={`px-2 py-1 rounded text-xs font-semibold ${isMajor ? 'bg-orange-200 text-orange-800' : 'bg-blue-200 text-blue-800'}`}>
                {changeType}
            </span>
        );
    };

    const handleExportCSV = async () => {
        try {
            setExportingCSV(true);
            await versionsApi.exportCSV(modelId);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to export CSV');
        } finally {
            setExportingCSV(false);
        }
    };

    const canApprove = user?.role === 'Validator' || user?.role === 'Admin';

    if (loading) return <div className="p-4">Loading versions...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;

    if (versions.length === 0) {
        return <div className="p-4 text-gray-500">No versions found</div>;
    }

    return (
        <div>
            {/* Header with Export Button */}
            <div className="flex justify-end mb-3">
                <button
                    onClick={handleExportCSV}
                    disabled={exportingCSV}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-400 text-sm"
                >
                    {exportingCSV ? 'Exporting...' : 'Export to CSV'}
                </button>
            </div>

            <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Production Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {versions.map((version) => (
                        <tr
                            key={version.version_id}
                            onClick={() => onVersionClick && onVersionClick(version)}
                            className="hover:bg-gray-50 cursor-pointer"
                        >
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{version.version_number}</td>
                            <td className="px-4 py-3 text-sm">
                                {version.change_type_name ? (
                                    <div>
                                        <div className="font-medium text-gray-900">{version.change_type_name}</div>
                                        {version.change_category_name && (
                                            <div className="text-xs text-gray-500">{version.change_category_name}</div>
                                        )}
                                        <div className="mt-1">{getChangeTypeBadge(version.change_type)}</div>
                                    </div>
                                ) : (
                                    getChangeTypeBadge(version.change_type)
                                )}
                            </td>
                            <td className="px-4 py-3 text-sm">{getStatusBadge(version.status)}</td>
                            <td className="px-4 py-3 text-sm">
                                {version.validation_request_id ? (
                                    <Link
                                        to={`/validation-workflow/${version.validation_request_id}`}
                                        onClick={(e) => e.stopPropagation()}
                                        className="text-blue-600 hover:text-blue-800 hover:underline text-xs"
                                    >
                                        Request #{version.validation_request_id}
                                        {version.validation_type === 'INTERIM' && (
                                            <span className="ml-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">
                                                INTERIM
                                            </span>
                                        )}
                                    </Link>
                                ) : (
                                    <span className="text-xs text-gray-400">-</span>
                                )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate" title={version.change_description}>
                                {version.change_description}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                                {version.production_date ? new Date(version.production_date).toLocaleDateString() : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                                {new Date(version.created_at).toLocaleDateString()}
                                {version.created_by_name && (
                                    <div className="text-xs text-gray-500">{version.created_by_name}</div>
                                )}
                            </td>
                            <td className="px-4 py-3 text-sm">
                                <div className="flex gap-2">
                                    {version.status === 'IN_VALIDATION' && canApprove && (
                                        <button
                                            onClick={(e) => handleApprove(e, version.version_id)}
                                            className="text-green-600 hover:text-green-800 font-medium"
                                        >
                                            Approve
                                        </button>
                                    )}
                                    {version.status === 'APPROVED' && (
                                        <button
                                            onClick={(e) => handleActivate(e, version.version_id)}
                                            className="text-blue-600 hover:text-blue-800 font-medium"
                                        >
                                            Activate
                                        </button>
                                    )}
                                    {version.status === 'DRAFT' && (
                                        <button
                                            onClick={(e) => handleDelete(e, version.version_id)}
                                            className="text-red-600 hover:text-red-800 font-medium"
                                        >
                                            Delete
                                        </button>
                                    )}
                                    {version.status === 'ACTIVE' && (
                                        <span className="text-xs text-gray-500 italic">Current</span>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>
        </div>
    );
};

export default VersionsList;

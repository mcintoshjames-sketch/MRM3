import React, { useEffect, useState } from 'react';
import api from '../api/client';

export interface ModelVersion {
    version_id: number;
    version_number: string;
    change_description: string | null;
    production_date: string | null;
    status: string;
}

interface VersionSelectorProps {
    modelId: number;
    filterStatus?: string;
    onSelect: (version: ModelVersion) => void;
}

const VersionSelector: React.FC<VersionSelectorProps> = ({ modelId, filterStatus, onSelect }) => {
    const [versions, setVersions] = useState<ModelVersion[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!modelId) return;

        const fetchVersions = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await api.get(`/models/${modelId}/versions`);
                setVersions(response.data || []);
            } catch (err) {
                console.error('Failed to fetch versions:', err);
                setError('Failed to load versions');
            } finally {
                setLoading(false);
            }
        };

        fetchVersions();
    }, [modelId]);

    const visibleVersions = filterStatus
        ? versions.filter((version) => version.status === filterStatus)
        : versions;

    return (
        <div className="mt-3 rounded border border-gray-200 bg-gray-50 p-3">
            <div className="text-sm font-semibold text-gray-700">Select a version</div>
            {loading && (
                <div className="mt-2 text-sm text-gray-500">Loading versions...</div>
            )}
            {error && (
                <div className="mt-2 text-sm text-red-600">{error}</div>
            )}
            {!loading && !error && visibleVersions.length === 0 && (
                <div className="mt-2 text-sm text-gray-500">
                    No {filterStatus ? filterStatus.toLowerCase() : ''} versions available.
                </div>
            )}
            {!loading && !error && visibleVersions.length > 0 && (
                <div className="mt-3 space-y-2">
                    {visibleVersions.map((version) => (
                        <button
                            key={version.version_id}
                            type="button"
                            onClick={() => onSelect(version)}
                            className="w-full rounded border border-gray-200 bg-white px-3 py-2 text-left hover:border-blue-400 hover:bg-blue-50"
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-800">
                                    {version.version_number}
                                </span>
                                <span className="text-xs text-gray-500">{version.status}</span>
                            </div>
                            <div className="mt-1 text-xs text-gray-600">
                                {version.change_description || 'No change description'}
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                                Production date: {version.production_date ? version.production_date.split('T')[0] : 'N/A'}
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default VersionSelector;

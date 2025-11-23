import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

interface LineageNode {
    model_id: number;
    model_name: string;
    dependency_type: string;
    description: string | null;
    depth: number;
    upstream?: LineageNode[];
    downstream?: LineageNode[];
}

interface LineageData {
    model: {
        model_id: number;
        model_name: string;
    };
    upstream?: LineageNode[];
    downstream?: LineageNode[];
}

interface Props {
    modelId: number;
    modelName: string;
}

export default function LineageViewer({ modelId, modelName }: Props) {
    const [lineageData, setLineageData] = useState<LineageData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both');
    const [maxDepth, setMaxDepth] = useState(5);
    const [includeInactive, setIncludeInactive] = useState(false);

    useEffect(() => {
        fetchLineage();
    }, [modelId, direction, maxDepth, includeInactive]);

    const fetchLineage = async () => {
        try {
            setLoading(true);
            setError(null);
            const params = new URLSearchParams({
                direction,
                max_depth: maxDepth.toString(),
                include_inactive: includeInactive.toString()
            });
            const response = await api.get(`/models/${modelId}/dependencies/lineage?${params.toString()}`);
            setLineageData(response.data);
        } catch (err: any) {
            console.error('Error fetching lineage:', err);
            setError(err.response?.data?.detail || 'Failed to load lineage data');
        } finally {
            setLoading(false);
        }
    };

    const renderNode = (node: LineageNode, isUpstream: boolean): JSX.Element => {
        const children = isUpstream ? node.upstream : node.downstream;
        const hasChildren = children && children.length > 0;

        return (
            <div key={`${node.model_id}-${node.depth}`} className="relative">
                {/* Node Card */}
                <div className={`relative z-10 group transition-all duration-200`}>
                    <div className={`flex items-start p-3 bg-white border rounded-lg shadow-sm hover:shadow-md transition-all ${isUpstream
                        ? 'border-green-200 hover:border-green-400'
                        : 'border-purple-200 hover:border-purple-400'
                        }`}>
                        <div className={`flex-shrink-0 mt-1.5 w-2.5 h-2.5 rounded-full ${isUpstream ? 'bg-green-400' : 'bg-purple-400'
                            }`} />

                        <div className="ml-3 flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                                <Link
                                    to={`/models/${node.model_id}`}
                                    className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate"
                                >
                                    {node.model_name}
                                </Link>
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${isUpstream ? 'bg-green-50 text-green-700' : 'bg-purple-50 text-purple-700'
                                    }`}>
                                    {node.dependency_type}
                                </span>
                            </div>
                            {node.description && (
                                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{node.description}</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Children */}
                {hasChildren && (
                    <div className="ml-4 pl-8 border-l-2 border-gray-100 mt-3 space-y-3 pb-1">
                        {children.map((child) => (
                            <div key={`${child.model_id}-${child.depth}`} className="relative">
                                {/* Horizontal Connector */}
                                <div className="absolute -left-8 top-6 w-8 h-0.5 bg-gray-100"></div>
                                {renderNode(child, isUpstream)}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    if (loading) {
        return (
            <div className="text-center py-8 text-gray-500">
                <svg className="animate-spin h-8 w-8 mx-auto mb-2 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading lineage data...
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <svg className="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-red-900">Error Loading Lineage</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
                <button
                    onClick={fetchLineage}
                    className="mt-4 inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200"
                >
                    Try Again
                </button>
            </div>
        );
    }

    const hasUpstream = lineageData?.upstream && lineageData.upstream.length > 0;
    const hasDownstream = lineageData?.downstream && lineageData.downstream.length > 0;

    if (!hasUpstream && !hasDownstream) {
        return (
            <div className="space-y-6">
                {/* Controls */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label htmlFor="direction-select-empty" className="block text-sm font-medium text-gray-700 mb-2">
                                Direction
                            </label>
                            <select
                                id="direction-select-empty"
                                value={direction}
                                onChange={(e) => setDirection(e.target.value as any)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                                <option value="both">Both (Upstream & Downstream)</option>
                                <option value="upstream">Upstream Only (Feeders)</option>
                                <option value="downstream">Downstream Only (Consumers)</option>
                            </select>
                        </div>
                        <div>
                            <label htmlFor="depth-select-empty" className="block text-sm font-medium text-gray-700 mb-2">
                                Max Depth
                            </label>
                            <select
                                id="depth-select-empty"
                                value={maxDepth}
                                onChange={(e) => setMaxDepth(Number(e.target.value))}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                                <option value="3">3 Levels</option>
                                <option value="5">5 Levels</option>
                                <option value="10">10 Levels</option>
                                <option value="20">20 Levels</option>
                            </select>
                        </div>
                        <div className="flex items-end">
                            <label className="flex items-center space-x-2">
                                <input
                                    type="checkbox"
                                    checked={includeInactive}
                                    onChange={(e) => setIncludeInactive(e.target.checked)}
                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <span className="text-sm font-medium text-gray-700">
                                    Include Inactive
                                </span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Empty State */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No Dependency Lineage</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        This model has no {direction === 'upstream' ? 'upstream feeders' : direction === 'downstream' ? 'downstream consumers' : 'dependency relationships'} in the data flow chain.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label htmlFor="direction-select" className="block text-sm font-medium text-gray-700 mb-2">
                            Direction
                        </label>
                        <select
                            id="direction-select"
                            value={direction}
                            onChange={(e) => setDirection(e.target.value as any)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="both">Both (Upstream & Downstream)</option>
                            <option value="upstream">Upstream Only (Feeders)</option>
                            <option value="downstream">Downstream Only (Consumers)</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="depth-select" className="block text-sm font-medium text-gray-700 mb-2">
                            Max Depth
                        </label>
                        <select
                            id="depth-select"
                            value={maxDepth}
                            onChange={(e) => setMaxDepth(Number(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="3">3 Levels</option>
                            <option value="5">5 Levels</option>
                            <option value="10">10 Levels</option>
                            <option value="20">20 Levels</option>
                        </select>
                    </div>
                    <div className="flex items-end">
                        <label className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                checked={includeInactive}
                                onChange={(e) => setIncludeInactive(e.target.checked)}
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="text-sm font-medium text-gray-700">
                                Include Inactive
                            </span>
                        </label>
                    </div>
                </div>
            </div>

            {/* Center Model */}
            <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-4 text-center">
                <div className="text-sm font-medium text-blue-600 uppercase tracking-wide mb-1">
                    Current Model
                </div>
                <div className="text-xl font-bold text-blue-900">
                    {modelName}
                </div>
            </div>

            {/* Upstream Lineage */}
            {hasUpstream && (direction === 'both' || direction === 'upstream') && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="bg-green-50 px-4 py-3 border-b border-green-200">
                        <div className="flex items-center">
                            <svg className="h-5 w-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
                            </svg>
                            <h3 className="text-lg font-medium text-green-900">
                                Upstream Dependencies (Feeders)
                            </h3>
                            <span className="ml-2 text-sm text-green-600">
                                {lineageData.upstream?.length} direct
                            </span>
                        </div>
                        <p className="text-sm text-green-700 mt-1">
                            Models that provide data to this model
                        </p>
                    </div>
                    <div className="p-6 space-y-6">
                        {lineageData.upstream?.map((node) => renderNode(node, true))}
                    </div>
                </div>
            )}

            {/* Downstream Lineage */}
            {hasDownstream && (direction === 'both' || direction === 'downstream') && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="bg-purple-50 px-4 py-3 border-b border-purple-200">
                        <div className="flex items-center">
                            <svg className="h-5 w-5 text-purple-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                            </svg>
                            <h3 className="text-lg font-medium text-purple-900">
                                Downstream Dependencies (Consumers)
                            </h3>
                            <span className="ml-2 text-sm text-purple-600">
                                {lineageData.downstream?.length} direct
                            </span>
                        </div>
                        <p className="text-sm text-purple-700 mt-1">
                            Models that consume data from this model
                        </p>
                    </div>
                    <div className="p-6 space-y-6">
                        {lineageData.downstream?.map((node) => renderNode(node, false))}
                    </div>
                </div>
            )}
        </div>
    );
}

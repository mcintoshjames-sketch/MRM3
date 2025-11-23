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
        const indent = node.depth * 24; // 24px per depth level
        const children = isUpstream ? node.upstream : node.downstream;

        return (
            <div key={`${node.model_id}-${node.depth}`} style={{ marginLeft: `${indent}px` }}>
                <div className="flex items-center py-2 border-b border-gray-100 hover:bg-gray-50">
                    <div className="flex-1">
                        <Link
                            to={`/models/${node.model_id}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                        >
                            {node.model_name}
                        </Link>
                        <span className="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            {node.dependency_type}
                        </span>
                        {node.description && (
                            <p className="text-sm text-gray-600 mt-1">{node.description}</p>
                        )}
                    </div>
                    <div className="text-xs text-gray-500">
                        Depth: {node.depth}
                    </div>
                </div>
                {children && children.length > 0 && (
                    <div>
                        {children.map((child) => renderNode(child, isUpstream))}
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
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Direction
                            </label>
                            <select
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
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Max Depth
                            </label>
                            <select
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
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Direction
                        </label>
                        <select
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
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Max Depth
                        </label>
                        <select
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
                    <div className="p-4">
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
                    <div className="p-4">
                        {lineageData.downstream?.map((node) => renderNode(node, false))}
                    </div>
                </div>
            )}
        </div>
    );
}

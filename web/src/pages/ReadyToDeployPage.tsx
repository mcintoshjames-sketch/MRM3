import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import FilterStatusBar from '../components/FilterStatusBar';
import StatFilterCard from '../components/StatFilterCard';
import { readyToDeployApi, ReadyToDeployItem } from '../api/versions';
import { useTableSort } from '../hooks/useTableSort';
import { useAuth } from '../contexts/AuthContext';

const ReadyToDeployPage: React.FC = () => {
    const { user } = useAuth();
    const [items, setItems] = useState<ReadyToDeployItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [myModelsOnly, setMyModelsOnly] = useState(false);
    type DeployFilterMode = 'all' | 'ready' | 'pending';
    const [filterMode, setFilterMode] = useState<DeployFilterMode>('all');

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await readyToDeployApi.getReadyToDeploy({ my_models_only: myModelsOnly });
            setItems(data);
        } catch (err) {
            console.error('Error fetching ready to deploy data:', err);
            setError('Failed to load ready to deploy data. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [myModelsOnly]);

    const baseData = useMemo(() => {
        if (!myModelsOnly || !user) {
            return items;
        }
        return items.filter(item => item.owner_id === user.user_id);
    }, [items, myModelsOnly, user]);

    const { totalCount, readyCount, pendingCount } = useMemo(() => {
        return {
            totalCount: baseData.length,
            readyCount: baseData.filter(item => !item.has_pending_task).length,
            pendingCount: baseData.filter(item => item.has_pending_task).length,
        };
    }, [baseData]);

    const filteredItems = useMemo(() => {
        switch (filterMode) {
            case 'ready':
                return baseData.filter(item => !item.has_pending_task);
            case 'pending':
                return baseData.filter(item => item.has_pending_task);
            default:
                return baseData;
        }
    }, [baseData, filterMode]);

    const { sortedData, requestSort, getSortIcon } = useTableSort<ReadyToDeployItem>(
        filteredItems,
        'days_since_approval',
        'desc'
    );

    const activeFilterLabel = filterMode === 'ready'
        ? 'Ready to Deploy'
        : filterMode === 'pending'
            ? 'Pending Tasks'
            : '';

    const exportCSV = () => {
        if (sortedData.length === 0) return;

        const headers = [
            'Model Name',
            'Version',
            'Region',
            'Owner',
            'Version Source',
            'Validation Status',
            'Approved Date',
            'Days Since Approval',
            'Has Pending Task'
        ];

        const rows = sortedData.map(item => [
            item.model_name,
            item.version_number,
            `${item.region_code} - ${item.region_name}`,
            item.owner_name,
            item.version_source,
            item.validation_status,
            item.validation_approved_date || '',
            item.days_since_approval.toString(),
            item.has_pending_task ? 'Yes' : 'No'
        ]);

        const csvContent = [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `ready_to_deploy_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    };

    const getStatusBadgeColor = (daysOld: number): string => {
        if (daysOld > 30) return 'bg-red-100 text-red-800';
        if (daysOld > 14) return 'bg-yellow-100 text-yellow-800';
        return 'bg-green-100 text-green-800';
    };

    const getVersionSourceBadge = (source: string): JSX.Element => {
        if (source === 'explicit') {
            return (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    Explicit
                </span>
            );
        }
        return (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                Inferred
            </span>
        );
    };

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-2xl font-semibold text-gray-900">Ready to Deploy</h1>
                        <p className="mt-1 text-sm text-gray-500">
                            Model versions with approved validations awaiting deployment by region
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <label className="flex items-center gap-2 text-sm text-gray-700">
                            <input
                                type="checkbox"
                                checked={myModelsOnly}
                                onChange={(e) => setMyModelsOnly(e.target.checked)}
                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            My Models Only
                        </label>
                        <button
                            onClick={fetchData}
                            disabled={loading}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                        >
                            {loading ? 'Loading...' : 'Refresh'}
                        </button>
                        <button
                            onClick={exportCSV}
                            disabled={sortedData.length === 0}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Error State */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-4">
                        <p className="text-red-800">{error}</p>
                    </div>
                )}

                {/* Summary Cards */}
                {!loading && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <StatFilterCard
                            label="Total Candidates"
                            count={totalCount}
                            isActive={filterMode === 'all'}
                            onClick={() => setFilterMode('all')}
                            colorScheme="blue"
                        />
                        <StatFilterCard
                            label="Ready to Deploy"
                            count={readyCount}
                            isActive={filterMode === 'ready'}
                            onClick={() => setFilterMode(prev => (prev === 'ready' ? 'all' : 'ready'))}
                            colorScheme="green"
                        />
                        <StatFilterCard
                            label="Pending Tasks"
                            count={pendingCount}
                            isActive={filterMode === 'pending'}
                            onClick={() => setFilterMode(prev => (prev === 'pending' ? 'all' : 'pending'))}
                            colorScheme="yellow"
                        />
                    </div>
                )}

                {!loading && filterMode !== 'all' && (
                    <FilterStatusBar
                        activeFilterLabel={activeFilterLabel}
                        onClear={() => setFilterMode('all')}
                        entityName="candidates"
                    />
                )}

                {/* Loading State */}
                {loading && (
                    <div className="flex justify-center items-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span className="ml-3 text-gray-600">Loading...</span>
                    </div>
                )}

                {/* Data Table */}
                {!loading && !error && (
                    <div className="bg-white shadow rounded-lg overflow-hidden">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('model_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Model
                                            {getSortIcon('model_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('version_number')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Version
                                            {getSortIcon('version_number')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('region_code')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Region
                                            {getSortIcon('region_code')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('owner_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Owner
                                            {getSortIcon('owner_name')}
                                        </div>
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Source
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('days_since_approval')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Days Since Approval
                                            {getSortIcon('days_since_approval')}
                                        </div>
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Task Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {sortedData.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                                            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            <p className="mt-2 text-sm font-medium">No versions ready to deploy</p>
                                            <p className="mt-1 text-sm text-gray-400">
                                                All validated versions have been deployed to their target regions.
                                            </p>
                                        </td>
                                    </tr>
                                ) : (
                                    sortedData.map((item) => (
                                        <tr key={`${item.version_id}-${item.region_id}`} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${item.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {item.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {item.version_number}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                                                    {item.region_code}
                                                </span>
                                                <span className="ml-2 text-sm text-gray-500">{item.region_name}</span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {item.owner_name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getVersionSourceBadge(item.version_source)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(item.days_since_approval)}`}>
                                                    {item.days_since_approval} days
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {item.has_pending_task ? (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                        Scheduled
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-gray-400">Not scheduled</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                <div className="flex gap-2">
                                                    <Link
                                                        to={`/models/${item.model_id}?tab=versions`}
                                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                                    >
                                                        View
                                                    </Link>
                                                    {!item.has_pending_task && (
                                                        <Link
                                                            to={`/models/${item.model_id}?tab=versions&deploy=${item.version_id}`}
                                                            className="text-green-600 hover:text-green-800 hover:underline"
                                                        >
                                                            Deploy
                                                        </Link>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Help Text */}
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <h3 className="text-sm font-medium text-blue-800">About Ready to Deploy</h3>
                    <ul className="mt-2 text-sm text-blue-700 list-disc list-inside space-y-1">
                        <li>Shows model versions that have passed validation but aren't yet deployed to each target region</li>
                        <li><span className="font-medium">Source</span>: "Explicit" means the user linked this version to the validation; "Inferred" means the system auto-suggested it</li>
                        <li>Color coding: <span className="text-green-700 font-medium">Green</span> (≤14 days), <span className="text-yellow-700 font-medium">Yellow</span> (15-30 days), <span className="text-red-700 font-medium">Red</span> (&gt;30 days since approval)</li>
                        <li>Use the "My Models Only" filter to see only models you own</li>
                        <li>Click "Deploy" to schedule a deployment task for that region, or "View" to see version details</li>
                    </ul>
                </div>
            </div>
        </Layout>
    );
};

export default ReadyToDeployPage;

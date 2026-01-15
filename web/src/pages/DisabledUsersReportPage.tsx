import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import client from '../api/client';
import { useTableSort } from '../hooks/useTableSort';

interface AffectedUser {
    role: string;
    user_id: number;
    full_name: string;
    email: string;
    azure_state: string | null;
    local_status: string;
}

interface DisabledUserModel {
    model_id: number;
    model_name: string;
    external_model_id: string | null;
    affected_users: AffectedUser[];
}

interface DisabledUsersReportResponse {
    total_affected_models: number;
    models: DisabledUserModel[];
}

// Flatten models to rows for table display and sorting
interface FlattenedRow {
    model_id: number;
    model_name: string;
    external_model_id: string | null;
    role: string;
    user_id: number;
    full_name: string;
    email: string;
    azure_state: string | null;
    local_status: string;
}

const DisabledUsersReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [reportData, setReportData] = useState<DisabledUsersReportResponse | null>(null);
    const [azureStateFilter, setAzureStateFilter] = useState<string>('');
    const [roleFilter, setRoleFilter] = useState<string>('');

    useEffect(() => {
        fetchReport();
    }, []);

    const fetchReport = async () => {
        try {
            setLoading(true);
            const response = await client.get('/models/disabled-users');
            setReportData(response.data);
        } catch (error) {
            console.error('Failed to fetch report:', error);
        } finally {
            setLoading(false);
        }
    };

    // Flatten models with affected users into rows for table display
    const flattenedRows: FlattenedRow[] = reportData?.models.flatMap(model =>
        model.affected_users.map(user => ({
            model_id: model.model_id,
            model_name: model.model_name,
            external_model_id: model.external_model_id,
            role: user.role,
            user_id: user.user_id,
            full_name: user.full_name,
            email: user.email,
            azure_state: user.azure_state,
            local_status: user.local_status,
        }))
    ) || [];

    // Apply filters
    const filteredRows = flattenedRows.filter(row => {
        if (azureStateFilter && row.azure_state !== azureStateFilter) return false;
        if (roleFilter && row.role !== roleFilter) return false;
        return true;
    });

    // Get unique values for filters
    const uniqueAzureStates = [...new Set(flattenedRows.map(r => r.azure_state).filter(Boolean))];
    const uniqueRoles = [...new Set(flattenedRows.map(r => r.role))];

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<FlattenedRow>(filteredRows, 'model_name');

    const getAzureStateBadge = (azureState: string | null) => {
        switch (azureState) {
            case 'NOT_FOUND':
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Hard Deleted
                    </span>
                );
            case 'SOFT_DELETED':
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        Soft Deleted
                    </span>
                );
            case 'EXISTS':
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        IT Lockout
                    </span>
                );
            default:
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        Disabled
                    </span>
                );
        }
    };

    const exportToCsv = () => {
        if (sortedData.length === 0) return;

        const headers = [
            'Model ID',
            'Model Name',
            'External Model ID',
            'Affected Role',
            'User ID',
            'User Name',
            'Email',
            'Azure State',
            'Local Status'
        ];

        const rows = sortedData.map(row => [
            row.model_id,
            row.model_name,
            row.external_model_id || '',
            row.role,
            row.user_id,
            row.full_name,
            row.email,
            row.azure_state || '',
            row.local_status
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `disabled_users_report_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (loading && !reportData) {
        return (
            <Layout>
                <div className="flex justify-center items-center h-64">
                    <p className="text-gray-500">Loading report...</p>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            Models with Disabled Users
                        </h1>
                        <p className="mt-1 text-sm text-gray-600">
                            Governance report showing models that have disabled users in key roles.
                            These models require role reassignment to ensure proper ownership and accountability.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={fetchReport}
                            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Refresh
                        </button>
                        <button
                            onClick={exportToCsv}
                            disabled={sortedData.length === 0}
                            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm font-medium text-gray-500">Total Affected Models</p>
                        <p className="text-2xl font-bold text-amber-600">{reportData?.total_affected_models || 0}</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm font-medium text-gray-500">Hard Deleted Users</p>
                        <p className="text-2xl font-bold text-red-600">
                            {flattenedRows.filter(r => r.azure_state === 'NOT_FOUND').length}
                        </p>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm font-medium text-gray-500">Soft Deleted Users</p>
                        <p className="text-2xl font-bold text-orange-600">
                            {flattenedRows.filter(r => r.azure_state === 'SOFT_DELETED').length}
                        </p>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm font-medium text-gray-500">IT Lockout Users</p>
                        <p className="text-2xl font-bold text-yellow-600">
                            {flattenedRows.filter(r => r.azure_state === 'EXISTS').length}
                        </p>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="flex flex-wrap gap-4 items-end">
                        <div>
                            <label htmlFor="azureStateFilter" className="block text-sm font-medium text-gray-700 mb-1">
                                Azure State
                            </label>
                            <select
                                id="azureStateFilter"
                                value={azureStateFilter}
                                onChange={(e) => setAzureStateFilter(e.target.value)}
                                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            >
                                <option value="">All States</option>
                                {uniqueAzureStates.map(state => (
                                    <option key={state} value={state || ''}>
                                        {state === 'NOT_FOUND' ? 'Hard Deleted' :
                                         state === 'SOFT_DELETED' ? 'Soft Deleted' :
                                         state === 'EXISTS' ? 'IT Lockout' : state}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label htmlFor="roleFilter" className="block text-sm font-medium text-gray-700 mb-1">
                                Role Type
                            </label>
                            <select
                                id="roleFilter"
                                value={roleFilter}
                                onChange={(e) => setRoleFilter(e.target.value)}
                                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            >
                                <option value="">All Roles</option>
                                {uniqueRoles.map(role => (
                                    <option key={role} value={role}>{role}</option>
                                ))}
                            </select>
                        </div>
                        {(azureStateFilter || roleFilter) && (
                            <button
                                onClick={() => {
                                    setAzureStateFilter('');
                                    setRoleFilter('');
                                }}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Clear Filters
                            </button>
                        )}
                    </div>
                </div>

                {/* Results Table */}
                <div className="bg-white rounded-lg shadow overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('model_id')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Model ID
                                            {getSortIcon('model_id')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('model_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Model Name
                                            {getSortIcon('model_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('role')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Affected Role
                                            {getSortIcon('role')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('full_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            User Name
                                            {getSortIcon('full_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('email')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Email
                                            {getSortIcon('email')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('azure_state')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Azure State
                                            {getSortIcon('azure_state')}
                                        </div>
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {sortedData.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center">
                                            <div className="text-gray-500">
                                                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                                <p className="mt-2 text-sm font-medium">No models with disabled users found</p>
                                                <p className="mt-1 text-xs text-gray-400">All model roles are assigned to active users</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    sortedData.map((row, index) => (
                                        <tr key={`${row.model_id}-${row.user_id}-${row.role}-${index}`} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {row.model_id}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${row.model_id}`}
                                                    className="text-sm font-medium text-blue-600 hover:text-blue-800"
                                                >
                                                    {row.model_name}
                                                </Link>
                                                {row.external_model_id && (
                                                    <p className="text-xs text-gray-500">{row.external_model_id}</p>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {row.role}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/users/${row.user_id}`}
                                                    className="text-sm text-blue-600 hover:text-blue-800"
                                                >
                                                    {row.full_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {row.email}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getAzureStateBadge(row.azure_state)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                <Link
                                                    to={`/models/${row.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800"
                                                >
                                                    Edit Model
                                                </Link>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    {sortedData.length > 0 && (
                        <div className="bg-gray-50 px-6 py-3 text-xs text-gray-500 border-t">
                            Showing {sortedData.length} of {flattenedRows.length} records
                            {(azureStateFilter || roleFilter) && ' (filtered)'}
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default DisabledUsersReportPage;

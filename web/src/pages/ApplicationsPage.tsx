import { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';

interface MapApplication {
    application_id: number;
    application_code: string;
    application_name: string;
    description: string | null;
    owner_name: string | null;
    owner_email: string | null;
    department: string | null;
    technology_stack: string | null;
    criticality_tier: string | null;
    status: string;
    external_url: string | null;
    created_at: string;
    updated_at: string;
}

// Exported content component for use in tabbed pages
export function ApplicationsContent() {
    const [applications, setApplications] = useState<MapApplication[]>([]);
    const [departments, setDepartments] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [searchTerm, setSearchTerm] = useState('');
    const [departmentFilter, setDepartmentFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('Active');
    const [criticalityFilter, setCriticalityFilter] = useState('');

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<MapApplication>(
        applications,
        'application_code'
    );

    useEffect(() => {
        fetchDepartments();
    }, []);

    useEffect(() => {
        fetchApplications();
    }, [searchTerm, departmentFilter, statusFilter, criticalityFilter]);

    const fetchDepartments = async () => {
        try {
            const response = await api.get('/map/departments');
            setDepartments(response.data);
        } catch (err) {
            console.error('Failed to fetch departments:', err);
        }
    };

    const fetchApplications = async () => {
        setLoading(true);
        setError(null);
        try {
            const params: Record<string, string> = {};
            if (searchTerm) params.search = searchTerm;
            if (departmentFilter) params.department = departmentFilter;
            if (statusFilter) params.status = statusFilter;
            if (criticalityFilter) params.criticality_tier = criticalityFilter;

            const response = await api.get('/map/applications', { params });
            setApplications(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load applications');
        } finally {
            setLoading(false);
        }
    };

    const getCriticalityColor = (tier: string | null) => {
        switch (tier) {
            case 'Critical':
                return 'bg-red-100 text-red-800';
            case 'High':
                return 'bg-orange-100 text-orange-800';
            case 'Medium':
                return 'bg-yellow-100 text-yellow-800';
            case 'Low':
                return 'bg-green-100 text-green-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Active':
                return 'bg-green-100 text-green-800';
            case 'In Development':
                return 'bg-blue-100 text-blue-800';
            case 'Decommissioned':
                return 'bg-gray-100 text-gray-500';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const clearFilters = () => {
        setSearchTerm('');
        setDepartmentFilter('');
        setStatusFilter('Active');
        setCriticalityFilter('');
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">MAP Application Inventory</h3>
                <p className="text-sm text-gray-500">
                    Read-only view of the Managed Application Portfolio
                </p>
            </div>

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow-md mb-4">
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                            Search
                        </label>
                        <input
                            type="text"
                            className="input-field text-sm"
                            placeholder="Code, name, or description..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                            Department
                        </label>
                        <select
                            className="input-field text-sm"
                            value={departmentFilter}
                            onChange={(e) => setDepartmentFilter(e.target.value)}
                        >
                            <option value="">All Departments</option>
                            {departments.map((dept) => (
                                <option key={dept} value={dept}>
                                    {dept}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                            Status
                        </label>
                        <select
                            className="input-field text-sm"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                        >
                            <option value="">All Statuses</option>
                            <option value="Active">Active</option>
                            <option value="In Development">In Development</option>
                            <option value="Decommissioned">Decommissioned</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                            Criticality
                        </label>
                        <select
                            className="input-field text-sm"
                            value={criticalityFilter}
                            onChange={(e) => setCriticalityFilter(e.target.value)}
                        >
                            <option value="">All Tiers</option>
                            <option value="Critical">Critical</option>
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                        </select>
                    </div>
                    <div className="flex items-end">
                        <button onClick={clearFilters} className="btn-secondary text-sm">
                            Clear Filters
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-64">Loading...</div>
            ) : (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    <div className="px-4 py-2 bg-gray-50 border-b text-sm text-gray-600">
                        {sortedData.length} application{sortedData.length !== 1 ? 's' : ''} found
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('application_code')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Code
                                            {getSortIcon('application_code')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('application_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Name
                                            {getSortIcon('application_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('department')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Department
                                            {getSortIcon('department')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('owner_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Owner
                                            {getSortIcon('owner_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('criticality_tier')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Criticality
                                            {getSortIcon('criticality_tier')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('status')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Status
                                            {getSortIcon('status')}
                                        </div>
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Technology
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {sortedData.length === 0 ? (
                                    <tr>
                                        <td
                                            colSpan={7}
                                            className="px-4 py-8 text-center text-gray-500"
                                        >
                                            No applications found matching the current filters.
                                        </td>
                                    </tr>
                                ) : (
                                    sortedData.map((app) => (
                                        <tr
                                            key={app.application_id}
                                            className={
                                                app.status === 'Decommissioned'
                                                    ? 'bg-gray-50 opacity-60'
                                                    : ''
                                            }
                                        >
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <span className="font-mono text-sm font-medium text-gray-900">
                                                    {app.application_code}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2">
                                                <div className="font-medium text-gray-900">
                                                    {app.application_name}
                                                </div>
                                                {app.description && (
                                                    <div className="text-xs text-gray-500 truncate max-w-xs">
                                                        {app.description}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-600">
                                                {app.department || '-'}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                {app.owner_name ? (
                                                    <div>
                                                        <div className="text-sm text-gray-900">
                                                            {app.owner_name}
                                                        </div>
                                                        {app.owner_email && (
                                                            <div className="text-xs text-gray-500">
                                                                {app.owner_email}
                                                            </div>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span className="text-sm text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                {app.criticality_tier ? (
                                                    <span
                                                        className={`px-2 py-1 text-xs rounded ${getCriticalityColor(app.criticality_tier)}`}
                                                    >
                                                        {app.criticality_tier}
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <span
                                                    className={`px-2 py-1 text-xs rounded ${getStatusColor(app.status)}`}
                                                >
                                                    {app.status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-600">
                                                {app.technology_stack || '-'}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

// Default export for standalone page (if needed in the future)
export default function ApplicationsPage() {
    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Applications</h2>
                <p className="text-gray-600 text-sm mt-1">
                    View the Managed Application Portfolio (MAP) inventory
                </p>
            </div>
            <ApplicationsContent />
        </Layout>
    );
}

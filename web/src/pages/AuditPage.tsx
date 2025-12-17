import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

interface AuditLog {
    log_id: number;
    entity_type: string;
    entity_id: number;
    action: string;
    user_id: number;
    changes: Record<string, unknown> | null;
    timestamp: string;
    user: User;
}

interface EntityOption {
    entity_id: number;
    label: string;
}

export default function AuditPage() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [entityTypes, setEntityTypes] = useState<string[]>([]);
    const [actions, setActions] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedLog, setExpandedLog] = useState<number | null>(null);

    // Filters
    const [filterEntityType, setFilterEntityType] = useState('');
    const [filterEntityId, setFilterEntityId] = useState('');
    const [filterAction, setFilterAction] = useState('');
    const [filterUserId, setFilterUserId] = useState('');

    // Entity dropdown state
    const [entityOptions, setEntityOptions] = useState<EntityOption[]>([]);
    const [entitySearchQuery, setEntitySearchQuery] = useState('');
    const [showEntityDropdown, setShowEntityDropdown] = useState(false);
    const [loadingEntities, setLoadingEntities] = useState(false);

    useEffect(() => {
        fetchInitialData();
    }, []);

    useEffect(() => {
        fetchLogs();
    }, [filterEntityType, filterEntityId, filterAction, filterUserId]);

    // Fetch entity options when entity type changes
    useEffect(() => {
        if (filterEntityType) {
            fetchEntityOptions(filterEntityType);
        } else {
            setEntityOptions([]);
            setEntitySearchQuery('');
            setFilterEntityId('');
        }
    }, [filterEntityType]);

    const fetchEntityOptions = async (entityType: string) => {
        setLoadingEntities(true);
        try {
            const response = await api.get(`/audit-logs/entities?entity_type=${encodeURIComponent(entityType)}`);
            setEntityOptions(response.data);
        } catch (error) {
            console.error('Failed to fetch entity options:', error);
            setEntityOptions([]);
        } finally {
            setLoadingEntities(false);
        }
    };

    const fetchInitialData = async () => {
        try {
            const [usersRes, entityTypesRes, actionsRes] = await Promise.all([
                api.get('/auth/users'),
                api.get('/audit-logs/entity-types'),
                api.get('/audit-logs/actions')
            ]);
            setUsers(usersRes.data);
            setEntityTypes(entityTypesRes.data);
            setActions(actionsRes.data);
        } catch (error) {
            console.error('Failed to fetch initial data:', error);
        }
    };

    const fetchLogs = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterEntityType) params.append('entity_type', filterEntityType);
            if (filterEntityId) params.append('entity_id', filterEntityId);
            if (filterAction) params.append('action', filterAction);
            if (filterUserId) params.append('user_id', filterUserId);

            const response = await api.get(`/audit-logs/?${params.toString()}`);
            setLogs(response.data);
        } catch (error) {
            console.error('Failed to fetch audit logs:', error);
        } finally {
            setLoading(false);
        }
    };

    const clearFilters = () => {
        setFilterEntityType('');
        setFilterEntityId('');
        setFilterAction('');
        setFilterUserId('');
        setEntitySearchQuery('');
        setEntityOptions([]);
        setShowEntityDropdown(false);
    };

    const getActionBadgeColor = (action: string) => {
        switch (action) {
            case 'CREATE':
                return 'bg-green-100 text-green-800';
            case 'UPDATE':
                return 'bg-blue-100 text-blue-800';
            case 'DELETE':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getEntityLink = (entityType: string, entityId: number) => {
        switch (entityType) {
            case 'Model':
                return `/models/${entityId}`;
            case 'Vendor':
                return `/vendors/${entityId}`;
            default:
                return null;
        }
    };

    const formatValue = (value: unknown): string => {
        if (value === null || value === undefined) {
            return 'null';
        }
        if (Array.isArray(value)) {
            if (value.length === 0) {
                return '[]';
            }
            // If array of objects, format each object
            if (typeof value[0] === 'object') {
                return value.map(item => JSON.stringify(item, null, 2)).join(', ');
            }
            return JSON.stringify(value);
        }
        if (typeof value === 'object') {
            return JSON.stringify(value, null, 2);
        }
        return String(value);
    };

    const formatChanges = (changes: Record<string, unknown> | null) => {
        if (!changes) return null;
        return Object.entries(changes).map(([key, value]) => {
            if (typeof value === 'object' && value !== null && 'old' in value && 'new' in value) {
                const change = value as { old: unknown; new: unknown };
                return (
                    <div key={key} className="mb-2">
                        <span className="font-medium">{key}:</span>
                        <div className="ml-4 text-sm">
                            <div className="text-red-600">- {formatValue(change.old)}</div>
                            <div className="text-green-600">+ {formatValue(change.new)}</div>
                        </div>
                    </div>
                );
            }
            return (
                <div key={key} className="mb-1">
                    <span className="font-medium">{key}:</span>
                    <div className="ml-4 text-sm whitespace-pre-wrap">{formatValue(value)}</div>
                </div>
            );
        });
    };

    const handleExportCSV = () => {
        if (logs.length === 0) return;

        // Create CSV content
        const headers = ['Log ID', 'Timestamp', 'Entity Type', 'Entity ID', 'Action', 'User', 'User Email', 'Changes'];
        const rows = logs.map(log => {
            const changesStr = log.changes ? JSON.stringify(log.changes).replace(/"/g, '""') : '';
            return [
                log.log_id,
                log.timestamp.split('T')[0] + ' ' + log.timestamp.split('T')[1].split('.')[0],
                log.entity_type,
                log.entity_id,
                log.action,
                log.user.full_name,
                log.user.email,
                `"${changesStr}"`
            ].join(',');
        });

        const csv = [headers.join(','), ...rows].join('\n');

        // Create and trigger download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    };

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Audit Logs</h2>
                {logs.length > 0 && (
                    <button
                        onClick={handleExportCSV}
                        className="btn-secondary"
                    >
                        Export CSV
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Filters</h3>
                    <button
                        onClick={clearFilters}
                        className="text-sm text-blue-600 hover:text-blue-800"
                    >
                        Clear All
                    </button>
                </div>
                <div className="grid grid-cols-4 gap-4">
                    <div>
                        <label htmlFor="entity_type" className="block text-sm font-medium mb-1">
                            Entity Type
                        </label>
                        <select
                            id="entity_type"
                            className="input-field"
                            value={filterEntityType}
                            onChange={(e) => setFilterEntityType(e.target.value)}
                        >
                            <option value="">All Types</option>
                            {[...entityTypes].sort().map((type) => (
                                <option key={type} value={type}>
                                    {type}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="relative">
                        <label htmlFor="entity_search" className="block text-sm font-medium mb-1">
                            Entity
                        </label>
                        {!filterEntityType ? (
                            <input
                                id="entity_search"
                                type="text"
                                className="input-field bg-gray-100 cursor-not-allowed"
                                placeholder="Select entity type first"
                                disabled
                            />
                        ) : loadingEntities ? (
                            <input
                                id="entity_search"
                                type="text"
                                className="input-field bg-gray-100"
                                placeholder="Loading entities..."
                                disabled
                            />
                        ) : (
                            <>
                                <input
                                    id="entity_search"
                                    type="text"
                                    className="input-field"
                                    value={entitySearchQuery}
                                    onChange={(e) => {
                                        setEntitySearchQuery(e.target.value);
                                        setShowEntityDropdown(true);
                                        if (e.target.value === '') {
                                            setFilterEntityId('');
                                        }
                                    }}
                                    onFocus={() => setShowEntityDropdown(true)}
                                    placeholder="Type to search..."
                                />
                                {showEntityDropdown && entityOptions.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                        {entityOptions
                                            .filter((opt) =>
                                                opt.label.toLowerCase().includes(entitySearchQuery.toLowerCase())
                                            )
                                            .slice(0, 50)
                                            .map((opt) => (
                                                <div
                                                    key={opt.entity_id}
                                                    className={`px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm ${
                                                        filterEntityId === String(opt.entity_id) ? 'bg-blue-50' : ''
                                                    }`}
                                                    onClick={() => {
                                                        setFilterEntityId(String(opt.entity_id));
                                                        setEntitySearchQuery(opt.label);
                                                        setShowEntityDropdown(false);
                                                    }}
                                                >
                                                    <span className="text-gray-500 mr-2">#{opt.entity_id}</span>
                                                    {opt.label}
                                                </div>
                                            ))}
                                        {entityOptions.filter((opt) =>
                                            opt.label.toLowerCase().includes(entitySearchQuery.toLowerCase())
                                        ).length === 0 && (
                                            <div className="px-4 py-2 text-sm text-gray-500">No matches found</div>
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                        {filterEntityId && (
                            <button
                                type="button"
                                className="absolute right-2 top-7 text-gray-400 hover:text-gray-600"
                                onClick={() => {
                                    setFilterEntityId('');
                                    setEntitySearchQuery('');
                                }}
                            >
                                ✕
                            </button>
                        )}
                    </div>
                    <div>
                        <label htmlFor="action" className="block text-sm font-medium mb-1">
                            Action
                        </label>
                        <select
                            id="action"
                            className="input-field"
                            value={filterAction}
                            onChange={(e) => setFilterAction(e.target.value)}
                        >
                            <option value="">All Actions</option>
                            {actions.map((action) => (
                                <option key={action} value={action}>
                                    {action}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label htmlFor="user" className="block text-sm font-medium mb-1">
                            Changed By
                        </label>
                        <select
                            id="user"
                            className="input-field"
                            value={filterUserId}
                            onChange={(e) => setFilterUserId(e.target.value)}
                        >
                            <option value="">All Users</option>
                            {users.map((user) => (
                                <option key={user.user_id} value={user.user_id}>
                                    {user.full_name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Results */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="px-6 py-3 bg-gray-50 border-b">
                    <span className="text-sm text-gray-600">
                        {loading ? 'Loading...' : `${logs.length} audit log entries`}
                    </span>
                </div>
                {loading ? (
                    <div className="p-6 text-center text-gray-500">Loading audit logs...</div>
                ) : logs.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No audit logs found matching the filters.
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Timestamp
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Action
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Entity
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Changed By
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Details
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {logs.map((log) => (
                                <>
                                    <tr key={log.log_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {new Date(log.timestamp).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span
                                                className={`px-2 py-1 text-xs rounded ${getActionBadgeColor(log.action)}`}
                                            >
                                                {log.action}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium">{log.entity_type}</div>
                                            {getEntityLink(log.entity_type, log.entity_id) ? (
                                                <Link
                                                    to={getEntityLink(log.entity_type, log.entity_id)!}
                                                    className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    ID: {log.entity_id}
                                                </Link>
                                            ) : (
                                                <div className="text-xs text-gray-500">
                                                    ID: {log.entity_id}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm">{log.user.full_name}</div>
                                            <div className="text-xs text-gray-500">{log.user.email}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {log.changes && Object.keys(log.changes).length > 0 ? (
                                                <button
                                                    onClick={() =>
                                                        setExpandedLog(
                                                            expandedLog === log.log_id ? null : log.log_id
                                                        )
                                                    }
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    {expandedLog === log.log_id ? 'Hide Changes' : 'View Changes'}
                                                </button>
                                            ) : (
                                                <span className="text-gray-400 text-sm">No details</span>
                                            )}
                                        </td>
                                    </tr>
                                    {expandedLog === log.log_id && log.changes && (
                                        <tr key={`${log.log_id}-details`}>
                                            <td colSpan={5} className="px-6 py-4 bg-gray-50">
                                                <div className="text-sm">
                                                    <h4 className="font-semibold mb-2">Changes:</h4>
                                                    <div className="bg-white p-3 rounded border">
                                                        {formatChanges(log.changes)}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </Layout>
    );
}

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';
import type { Region } from '../api/regions';
import { lobApi, LOBUnit } from '../api/lob';

interface LOBBrief {
    lob_id: number;
    code: string;
    name: string;
    level: number;
    full_path: string;
}

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    regions: Region[];
    lob_id: number | null;
    lob: LOBBrief | null;
}

interface EntraUser {
    entra_id: string;
    user_principal_name: string;
    display_name: string;
    given_name: string | null;
    surname: string | null;
    mail: string;
    job_title: string | null;
    department: string | null;
    office_location: string | null;
    mobile_phone: string | null;
    account_enabled: boolean;
}

// Exported content component for use in tabbed pages
export function UsersContent() {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [lobUnits, setLobUnits] = useState<LOBUnit[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [formData, setFormData] = useState({
        email: '',
        full_name: '',
        password: '',
        role: 'User',
        region_ids: [] as number[],
        lob_id: null as number | null
    });

    // LOB search state for searchable dropdown
    const [lobSearch, setLobSearch] = useState('');
    const [showLobDropdown, setShowLobDropdown] = useState(false);

    // Entra directory state
    const [showEntraModal, setShowEntraModal] = useState(false);
    const [entraSearch, setEntraSearch] = useState('');
    const [entraUsers, setEntraUsers] = useState<EntraUser[]>([]);
    const [entraLoading, setEntraLoading] = useState(false);
    const [selectedEntraUser, setSelectedEntraUser] = useState<EntraUser | null>(null);
    const [provisionRole, setProvisionRole] = useState('User');
    const [provisionRegionIds, setProvisionRegionIds] = useState<number[]>([]);
    const [provisionLobId, setProvisionLobId] = useState<number | null>(null);
    const [provisionLobSearch, setProvisionLobSearch] = useState('');
    const [showProvisionLobDropdown, setShowProvisionLobDropdown] = useState(false);

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<User>(users, 'full_name');

    useEffect(() => {
        fetchUsers();
        fetchRegions();
        fetchLobUnits();
    }, []);

    const fetchLobUnits = async () => {
        try {
            const data = await lobApi.getLOBUnits(true);
            setLobUnits(data);
        } catch (error) {
            console.error('Failed to fetch LOB units:', error);
        }
    };

    const fetchUsers = async () => {
        try {
            const response = await api.get('/auth/users');
            setUsers(response.data);
        } catch (error) {
            console.error('Failed to fetch users:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (error) {
            console.error('Failed to fetch regions:', error);
        }
    };

    const resetForm = () => {
        setFormData({ email: '', full_name: '', password: '', role: 'User', region_ids: [], lob_id: null });
        setLobSearch('');
        setShowLobDropdown(false);
        setEditingUser(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate LOB selection for new users (required)
        if (!editingUser && !formData.lob_id) {
            alert('Line of Business (LOB) is required for all users');
            return;
        }

        try {
            if (editingUser) {
                const updatePayload: Record<string, any> = {};
                if (formData.email !== editingUser.email) updatePayload.email = formData.email;
                if (formData.full_name !== editingUser.full_name) updatePayload.full_name = formData.full_name;
                if (formData.role !== editingUser.role) updatePayload.role = formData.role;
                if (formData.password) updatePayload.password = formData.password;

                // Always include region_ids for Regional Approvers (or to clear regions when changing role)
                if (formData.role === 'Regional Approver' || editingUser.role === 'Regional Approver') {
                    updatePayload.region_ids = formData.region_ids;
                }

                // Include lob_id if changed
                if (formData.lob_id !== editingUser.lob_id) {
                    updatePayload.lob_id = formData.lob_id;
                }

                await api.patch(`/auth/users/${editingUser.user_id}`, updatePayload);
            } else {
                await api.post('/auth/register', formData);
            }
            resetForm();
            fetchUsers();
        } catch (error) {
            console.error('Failed to save user:', error);
        }
    };

    const handleEdit = (user: User) => {
        setEditingUser(user);
        setFormData({
            email: user.email,
            full_name: user.full_name,
            password: '',
            role: user.role,
            region_ids: user.regions?.map(r => r.region_id) || [],
            lob_id: user.lob_id
        });
        // Set LOB search to current LOB with org_unit if exists
        if (user.lob) {
            const lobUnit = lobUnits.find(l => l.lob_id === user.lob_id);
            if (lobUnit) {
                setLobSearch(`[${lobUnit.org_unit}] ${lobUnit.full_path}`);
            } else {
                setLobSearch(user.lob.full_path);
            }
        } else {
            setLobSearch('');
        }
        setShowForm(true);
    };

    const handleDelete = async (userId: number) => {
        if (userId === currentUser?.user_id) {
            alert('Cannot delete your own account');
            return;
        }
        if (!confirm('Are you sure you want to delete this user?')) return;

        try {
            await api.delete(`/auth/users/${userId}`);
            fetchUsers();
        } catch (error) {
            console.error('Failed to delete user:', error);
        }
    };

    const searchEntraDirectory = async () => {
        setEntraLoading(true);
        try {
            const response = await api.get(`/auth/entra/users?search=${encodeURIComponent(entraSearch)}`);
            setEntraUsers(response.data);
        } catch (error) {
            console.error('Failed to search Entra directory:', error);
        } finally {
            setEntraLoading(false);
        }
    };

    const provisionEntraUser = async () => {
        if (!selectedEntraUser) return;

        // Validate LOB selection (required)
        if (!provisionLobId) {
            alert('Line of Business (LOB) is required for all users');
            return;
        }

        try {
            const payload: any = {
                entra_id: selectedEntraUser.entra_id,
                role: provisionRole,
                lob_id: provisionLobId
            };

            // Include region_ids for Regional Approvers
            if (provisionRole === 'Regional Approver') {
                payload.region_ids = provisionRegionIds;
            }

            await api.post('/auth/entra/provision', payload);
            setShowEntraModal(false);
            setSelectedEntraUser(null);
            setEntraSearch('');
            setEntraUsers([]);
            setProvisionRole('User');
            setProvisionRegionIds([]);
            setProvisionLobId(null);
            setProvisionLobSearch('');
            setShowProvisionLobDropdown(false);
            fetchUsers();
        } catch (error: any) {
            console.error('Failed to provision user:', error);
            alert(error.response?.data?.detail || 'Failed to provision user');
        }
    };

    const closeEntraModal = () => {
        setShowEntraModal(false);
        setSelectedEntraUser(null);
        setEntraSearch('');
        setEntraUsers([]);
        setProvisionRole('User');
        setProvisionRegionIds([]);
        setProvisionLobId(null);
        setProvisionLobSearch('');
        setShowProvisionLobDropdown(false);
    };

    if (loading) {
        return <div className="flex items-center justify-center h-64">Loading...</div>;
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Users</h3>
                <div className="flex gap-2">
                    {currentUser?.role === 'Admin' && (
                        <button
                            onClick={() => setShowEntraModal(true)}
                            className="btn-primary bg-blue-700 hover:bg-blue-800"
                        >
                            Import from Entra
                        </button>
                    )}
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + Add User
                    </button>
                </div>
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingUser ? 'Edit User' : 'Create New User'}
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="email" className="block text-sm font-medium mb-2">
                                    Email
                                </label>
                                <input
                                    id="email"
                                    type="email"
                                    className="input-field"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="full_name" className="block text-sm font-medium mb-2">
                                    Full Name
                                </label>
                                <input
                                    id="full_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.full_name}
                                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="password" className="block text-sm font-medium mb-2">
                                    Password {editingUser && '(leave blank to keep current)'}
                                </label>
                                <input
                                    id="password"
                                    type="password"
                                    className="input-field"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    required={!editingUser}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="role" className="block text-sm font-medium mb-2">
                                    Role
                                </label>
                                <select
                                    id="role"
                                    className="input-field"
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value, region_ids: [] })}
                                >
                                    <option value="User">User</option>
                                    <option value="Validator">Validator</option>
                                    <option value="Admin">Admin</option>
                                    <option value="Global Approver">Global Approver</option>
                                    <option value="Regional Approver">Regional Approver</option>
                                </select>
                            </div>
                        </div>

                        {/* LOB (Line of Business) Selection */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">
                                Line of Business (LOB) *
                            </label>
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="Type to search LOB units..."
                                    value={lobSearch}
                                    onChange={(e) => {
                                        setLobSearch(e.target.value);
                                        setShowLobDropdown(true);
                                    }}
                                    onFocus={() => setShowLobDropdown(true)}
                                    className="input-field"
                                />
                                {showLobDropdown && lobSearch.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                        {lobUnits
                                            .filter((lob) =>
                                                lob.full_path.toLowerCase().includes(lobSearch.toLowerCase()) ||
                                                lob.code.toLowerCase().includes(lobSearch.toLowerCase()) ||
                                                lob.name.toLowerCase().includes(lobSearch.toLowerCase()) ||
                                                lob.org_unit.toLowerCase().includes(lobSearch.toLowerCase())
                                            )
                                            .slice(0, 50)
                                            .map((lob) => (
                                                <div
                                                    key={lob.lob_id}
                                                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                    onClick={() => {
                                                        setFormData({ ...formData, lob_id: lob.lob_id });
                                                        setLobSearch(`[${lob.org_unit}] ${lob.full_path}`);
                                                        setShowLobDropdown(false);
                                                    }}
                                                >
                                                    <div className="font-medium">[{lob.org_unit}] {lob.full_path}</div>
                                                    <div className="text-xs text-gray-500">Code: {lob.code}</div>
                                                </div>
                                            ))}
                                        {lobUnits.filter(lob =>
                                            lob.full_path.toLowerCase().includes(lobSearch.toLowerCase()) ||
                                            lob.code.toLowerCase().includes(lobSearch.toLowerCase()) ||
                                            lob.org_unit.toLowerCase().includes(lobSearch.toLowerCase())
                                        ).length === 0 && (
                                            <div className="px-4 py-2 text-sm text-gray-500">No results found</div>
                                        )}
                                    </div>
                                )}
                                {formData.lob_id && (
                                    <p className="mt-1 text-sm text-green-600">
                                        ✓ Selected: [{lobUnits.find(l => l.lob_id === formData.lob_id)?.org_unit}] {lobUnits.find(l => l.lob_id === formData.lob_id)?.full_path || 'Unknown'}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Region Selection for Regional Approvers */}
                        {formData.role === 'Regional Approver' && (
                            <div className="mb-4 p-4 border border-gray-200 rounded-lg">
                                <label className="block text-sm font-medium mb-2">
                                    Authorized Regions *
                                </label>
                                <div className="grid grid-cols-2 gap-2">
                                    {regions.map((region) => (
                                        <label key={region.region_id} className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={formData.region_ids.includes(region.region_id)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setFormData({ ...formData, region_ids: [...formData.region_ids, region.region_id] });
                                                    } else {
                                                        setFormData({ ...formData, region_ids: formData.region_ids.filter(id => id !== region.region_id) });
                                                    }
                                                }}
                                                className="rounded"
                                            />
                                            <span>{region.name} ({region.code})</span>
                                        </label>
                                    ))}
                                </div>
                                {formData.region_ids.length === 0 && (
                                    <p className="text-sm text-red-600 mt-2">At least one region must be selected for Regional Approvers</p>
                                )}
                            </div>
                        )}

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">
                                {editingUser ? 'Update' : 'Create'}
                            </button>
                            <button type="button" onClick={resetForm} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('user_id')}
                            >
                                <div className="flex items-center gap-2">
                                    ID
                                    {getSortIcon('user_id')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('full_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Full Name
                                    {getSortIcon('full_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('email')}
                            >
                                <div className="flex items-center gap-2">
                                    Email
                                    {getSortIcon('email')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('role')}
                            >
                                <div className="flex items-center gap-2">
                                    Role
                                    {getSortIcon('role')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('lob.full_path')}
                            >
                                <div className="flex items-center gap-2">
                                    LOB
                                    {getSortIcon('lob.full_path')}
                                </div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Regions
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                                    No users yet. Click "Add User" to create one.
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((user) => (
                                <tr key={user.user_id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {user.user_id}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                                        <Link
                                            to={`/users/${user.user_id}`}
                                            className="text-blue-600 hover:text-blue-800"
                                        >
                                            {user.full_name}
                                        </Link>
                                        {user.user_id === currentUser?.user_id && (
                                            <span className="ml-2 text-xs text-blue-600">(You)</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {user.email}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${
                                            user.role === 'Admin'
                                                ? 'bg-purple-100 text-purple-800'
                                                : user.role === 'Validator'
                                                    ? 'bg-green-100 text-green-800'
                                                    : user.role === 'Global Approver'
                                                        ? 'bg-blue-100 text-blue-800'
                                                        : user.role === 'Regional Approver'
                                                            ? 'bg-orange-100 text-orange-800'
                                                            : 'bg-gray-100 text-gray-800'
                                        }`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        {user.lob ? (
                                            <span className="text-gray-700" title={user.lob.full_path}>
                                                {user.lob.name}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">—</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        {user.regions && user.regions.length > 0 ? (
                                            <div className="flex flex-wrap gap-1">
                                                {user.regions.map(r => (
                                                    <span key={r.region_id} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                                                        {r.code}
                                                    </span>
                                                ))}
                                            </div>
                                        ) : (
                                            <span className="text-gray-400">—</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/users/${user.user_id}`}
                                            className="text-blue-600 hover:text-blue-800 text-sm mr-3"
                                        >
                                            View
                                        </Link>
                                        <button
                                            onClick={() => handleEdit(user)}
                                            className="text-blue-600 hover:text-blue-800 text-sm mr-3"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={() => handleDelete(user.user_id)}
                                            className={`text-sm ${
                                                user.user_id === currentUser?.user_id
                                                    ? 'text-gray-400 cursor-not-allowed'
                                                    : 'text-red-600 hover:text-red-800'
                                            }`}
                                            disabled={user.user_id === currentUser?.user_id}
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Entra Directory Lookup Modal */}
            {showEntraModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
                        <div className="p-6 border-b flex-shrink-0">
                            <div className="flex justify-between items-center">
                                <h3 className="text-lg font-bold">
                                    Microsoft Entra Directory Lookup
                                </h3>
                                <button
                                    onClick={closeEntraModal}
                                    className="text-gray-500 hover:text-gray-700"
                                >
                                    ✕
                                </button>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">
                                Search for employees in the organizational directory to add as application users.
                            </p>
                        </div>

                        <div className="p-6 flex-1 overflow-y-auto">
                            <div className="flex gap-2 mb-4">
                                <input
                                    type="text"
                                    className="input-field flex-1"
                                    placeholder="Search by name, email, department, or job title..."
                                    value={entraSearch}
                                    onChange={(e) => setEntraSearch(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && searchEntraDirectory()}
                                />
                                <button
                                    onClick={searchEntraDirectory}
                                    className="btn-primary"
                                    disabled={entraLoading}
                                >
                                    {entraLoading ? 'Searching...' : 'Search'}
                                </button>
                            </div>

                            <div className="border rounded max-h-80 overflow-y-auto">
                                {entraUsers.length === 0 ? (
                                    <div className="p-4 text-center text-gray-500">
                                        {entraSearch
                                            ? 'No users found. Try a different search term.'
                                            : 'Enter a search term to find employees in the directory.'}
                                    </div>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50 sticky top-0">
                                            <tr>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Name
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Email
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Title
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Department
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Office
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {entraUsers.map((entraUser) => (
                                                <tr
                                                    key={entraUser.entra_id}
                                                    onClick={() => setSelectedEntraUser(entraUser)}
                                                    className={`cursor-pointer hover:bg-blue-50 ${
                                                        selectedEntraUser?.entra_id === entraUser.entra_id
                                                            ? 'bg-blue-100'
                                                            : ''
                                                    }`}
                                                >
                                                    <td className="px-4 py-2 text-sm font-medium">
                                                        {entraUser.display_name}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm">
                                                        {entraUser.mail}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm">
                                                        {entraUser.job_title || '-'}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm">
                                                        {entraUser.department || '-'}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm">
                                                        {entraUser.office_location || '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {selectedEntraUser && (
                                <div className="mt-4 p-4 bg-blue-50 rounded border border-blue-200">
                                    <h4 className="font-medium mb-2">
                                        Selected: {selectedEntraUser.display_name}
                                    </h4>
                                    <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                                        <div>
                                            <span className="text-gray-600">Email:</span>{' '}
                                            {selectedEntraUser.mail}
                                        </div>
                                        <div>
                                            <span className="text-gray-600">Title:</span>{' '}
                                            {selectedEntraUser.job_title || 'N/A'}
                                        </div>
                                        <div>
                                            <span className="text-gray-600">Department:</span>{' '}
                                            {selectedEntraUser.department || 'N/A'}
                                        </div>
                                        <div>
                                            <span className="text-gray-600">Phone:</span>{' '}
                                            {selectedEntraUser.mobile_phone || 'N/A'}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-4 mb-3">
                                            <label className="text-sm font-medium">
                                                Application Role:
                                            </label>
                                            <select
                                                className="input-field w-auto"
                                                value={provisionRole}
                                                onChange={(e) => {
                                                    setProvisionRole(e.target.value);
                                                    setProvisionRegionIds([]);
                                                }}
                                            >
                                                <option value="User">User</option>
                                                <option value="Validator">Validator</option>
                                                <option value="Admin">Admin</option>
                                                <option value="Global Approver">Global Approver</option>
                                                <option value="Regional Approver">Regional Approver</option>
                                            </select>
                                        </div>

                                        {/* LOB Selection (Required) */}
                                        <div className="mb-3">
                                            <label className="block text-sm font-medium mb-1">
                                                Line of Business (LOB) *
                                            </label>
                                            <div className="relative">
                                                <input
                                                    type="text"
                                                    placeholder="Type to search LOB units..."
                                                    value={provisionLobSearch}
                                                    onChange={(e) => {
                                                        setProvisionLobSearch(e.target.value);
                                                        setShowProvisionLobDropdown(true);
                                                    }}
                                                    onFocus={() => setShowProvisionLobDropdown(true)}
                                                    className="input-field"
                                                />
                                                {showProvisionLobDropdown && provisionLobSearch.length > 0 && (
                                                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-40 overflow-y-auto">
                                                        {lobUnits
                                                            .filter((lob) =>
                                                                lob.full_path.toLowerCase().includes(provisionLobSearch.toLowerCase()) ||
                                                                lob.code.toLowerCase().includes(provisionLobSearch.toLowerCase()) ||
                                                                lob.name.toLowerCase().includes(provisionLobSearch.toLowerCase()) ||
                                                                lob.org_unit.toLowerCase().includes(provisionLobSearch.toLowerCase())
                                                            )
                                                            .slice(0, 30)
                                                            .map((lob) => (
                                                                <div
                                                                    key={lob.lob_id}
                                                                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                                    onClick={() => {
                                                                        setProvisionLobId(lob.lob_id);
                                                                        setProvisionLobSearch(`[${lob.org_unit}] ${lob.full_path}`);
                                                                        setShowProvisionLobDropdown(false);
                                                                    }}
                                                                >
                                                                    <div className="font-medium">[{lob.org_unit}] {lob.full_path}</div>
                                                                    <div className="text-xs text-gray-500">Code: {lob.code}</div>
                                                                </div>
                                                            ))}
                                                        {lobUnits.filter(lob =>
                                                            lob.full_path.toLowerCase().includes(provisionLobSearch.toLowerCase()) ||
                                                            lob.code.toLowerCase().includes(provisionLobSearch.toLowerCase()) ||
                                                            lob.org_unit.toLowerCase().includes(provisionLobSearch.toLowerCase())
                                                        ).length === 0 && (
                                                            <div className="px-4 py-2 text-sm text-gray-500">No results found</div>
                                                        )}
                                                    </div>
                                                )}
                                                {provisionLobId && (
                                                    <p className="mt-1 text-sm text-green-600">
                                                        ✓ Selected: [{lobUnits.find(l => l.lob_id === provisionLobId)?.org_unit}] {lobUnits.find(l => l.lob_id === provisionLobId)?.full_path || 'Unknown'}
                                                    </p>
                                                )}
                                                {!provisionLobId && (
                                                    <p className="mt-1 text-sm text-red-600">LOB selection is required</p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Region Selection for Regional Approvers */}
                                        {provisionRole === 'Regional Approver' && (
                                            <div className="mt-3 p-3 border border-gray-200 rounded-lg">
                                                <label className="block text-sm font-medium mb-2">
                                                    Authorized Regions *
                                                </label>
                                                <div className="grid grid-cols-2 gap-2">
                                                    {regions.map((region) => (
                                                        <label key={region.region_id} className="flex items-center gap-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={provisionRegionIds.includes(region.region_id)}
                                                                onChange={(e) => {
                                                                    if (e.target.checked) {
                                                                        setProvisionRegionIds([...provisionRegionIds, region.region_id]);
                                                                    } else {
                                                                        setProvisionRegionIds(provisionRegionIds.filter(id => id !== region.region_id));
                                                                    }
                                                                }}
                                                                className="rounded"
                                                            />
                                                            <span className="text-sm">{region.name} ({region.code})</span>
                                                        </label>
                                                    ))}
                                                </div>
                                                {provisionRegionIds.length === 0 && (
                                                    <p className="text-sm text-red-600 mt-2">At least one region must be selected for Regional Approvers</p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="p-6 border-t bg-gray-50 flex justify-end gap-2 flex-shrink-0">
                            <button onClick={closeEntraModal} className="btn-secondary">
                                Cancel
                            </button>
                            <button
                                onClick={provisionEntraUser}
                                className="btn-primary"
                                disabled={
                                    !selectedEntraUser ||
                                    !provisionLobId ||
                                    (provisionRole === 'Regional Approver' && provisionRegionIds.length === 0)
                                }
                            >
                                Add to Application
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Default export for standalone page (used by /users/:id routes)
export default function UsersPage() {
    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Users</h2>
                <p className="text-gray-600 text-sm mt-1">Manage application users and permissions</p>
            </div>
            <UsersContent />
        </Layout>
    );
}

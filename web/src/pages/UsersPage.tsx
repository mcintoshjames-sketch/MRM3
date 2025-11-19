import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
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

export default function UsersPage() {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [formData, setFormData] = useState({
        email: '',
        full_name: '',
        password: '',
        role: 'User'
    });

    // Entra directory state
    const [showEntraModal, setShowEntraModal] = useState(false);
    const [entraSearch, setEntraSearch] = useState('');
    const [entraUsers, setEntraUsers] = useState<EntraUser[]>([]);
    const [entraLoading, setEntraLoading] = useState(false);
    const [selectedEntraUser, setSelectedEntraUser] = useState<EntraUser | null>(null);
    const [provisionRole, setProvisionRole] = useState('User');

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<User>(users, 'full_name');

    useEffect(() => {
        fetchUsers();
    }, []);

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

    const resetForm = () => {
        setFormData({ email: '', full_name: '', password: '', role: 'User' });
        setEditingUser(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingUser) {
                const updatePayload: Record<string, string> = {};
                if (formData.email !== editingUser.email) updatePayload.email = formData.email;
                if (formData.full_name !== editingUser.full_name) updatePayload.full_name = formData.full_name;
                if (formData.role !== editingUser.role) updatePayload.role = formData.role;
                if (formData.password) updatePayload.password = formData.password;

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
            role: user.role
        });
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

        try {
            await api.post('/auth/entra/provision', {
                entra_id: selectedEntraUser.entra_id,
                role: provisionRole
            });
            setShowEntraModal(false);
            setSelectedEntraUser(null);
            setEntraSearch('');
            setEntraUsers([]);
            setProvisionRole('User');
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
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Users</h2>
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
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                >
                                    <option value="User">User</option>
                                    <option value="Validator">Validator</option>
                                    <option value="Admin">Admin</option>
                                </select>
                            </div>
                        </div>
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
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
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
                                                    : 'bg-gray-100 text-gray-800'
                                        }`}>
                                            {user.role}
                                        </span>
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
                                    <div className="flex items-center gap-4">
                                        <label className="text-sm font-medium">
                                            Application Role:
                                        </label>
                                        <select
                                            className="input-field w-auto"
                                            value={provisionRole}
                                            onChange={(e) => setProvisionRole(e.target.value)}
                                        >
                                            <option value="User">User</option>
                                            <option value="Validator">Validator</option>
                                            <option value="Admin">Admin</option>
                                        </select>
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
                                disabled={!selectedEntraUser}
                            >
                                Add to Application
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

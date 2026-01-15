import { useState, useEffect } from 'react';
import api from '../api/client';
import { useTableSort } from '../hooks/useTableSort';
import { useAuth } from '../contexts/AuthContext';
import { isAdmin } from '../utils/roleUtils';

interface EntraUser {
    object_id: string;
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
    in_recycle_bin: boolean;
    deleted_datetime: string | null;
}

interface FormData {
    user_principal_name: string;
    display_name: string;
    given_name: string;
    surname: string;
    mail: string;
    job_title: string;
    department: string;
    office_location: string;
    mobile_phone: string;
    account_enabled: boolean;
}

const emptyForm: FormData = {
    user_principal_name: '',
    display_name: '',
    given_name: '',
    surname: '',
    mail: '',
    job_title: '',
    department: '',
    office_location: '',
    mobile_phone: '',
    account_enabled: true
};

// Exported content component for use in tabbed pages
export function EntraDirectoryContent() {
    const { user } = useAuth();
    const [entraUsers, setEntraUsers] = useState<EntraUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingUser, setEditingUser] = useState<EntraUser | null>(null);
    const [formData, setFormData] = useState<FormData>(emptyForm);
    const [error, setError] = useState<string | null>(null);

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<EntraUser>(entraUsers, 'display_name');

    const userIsAdmin = isAdmin(user);

    useEffect(() => {
        fetchEntraUsers();
    }, []);

    const fetchEntraUsers = async () => {
        try {
            // Fetch all users (empty search returns all)
            const response = await api.get('/auth/entra/users');
            setEntraUsers(response.data);
        } catch (err) {
            console.error('Failed to fetch Entra users:', err);
            setError('Failed to load directory users');
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData(emptyForm);
        setEditingUser(null);
        setShowForm(false);
        setError(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            if (editingUser) {
                await api.patch(`/auth/entra/users/${editingUser.object_id}`, formData);
            } else {
                await api.post('/auth/entra/users', formData);
            }
            resetForm();
            fetchEntraUsers();
        } catch (err: unknown) {
            const axiosError = err as { response?: { data?: { detail?: string } } };
            setError(axiosError.response?.data?.detail || 'Failed to save directory user');
        }
    };

    const handleEdit = (entraUser: EntraUser) => {
        setEditingUser(entraUser);
        setFormData({
            user_principal_name: entraUser.user_principal_name,
            display_name: entraUser.display_name,
            given_name: entraUser.given_name || '',
            surname: entraUser.surname || '',
            mail: entraUser.mail,
            job_title: entraUser.job_title || '',
            department: entraUser.department || '',
            office_location: entraUser.office_location || '',
            mobile_phone: entraUser.mobile_phone || '',
            account_enabled: entraUser.account_enabled
        });
        setShowForm(true);
        setError(null);
    };

    const handleMoveToRecycleBin = async (objectId: string) => {
        if (!confirm('Move this user to recycle bin? They will be marked as soft-deleted.')) return;

        try {
            await api.patch(`/auth/entra/users/${objectId}`, {
                in_recycle_bin: true,
                deleted_datetime: new Date().toISOString()
            });
            fetchEntraUsers();
        } catch (err: unknown) {
            const axiosError = err as { response?: { data?: { detail?: string } } };
            setError(axiosError.response?.data?.detail || 'Failed to move user to recycle bin');
        }
    };

    const handleRestoreFromRecycleBin = async (objectId: string) => {
        if (!confirm('Restore this user from recycle bin?')) return;

        try {
            await api.patch(`/auth/entra/users/${objectId}`, {
                in_recycle_bin: false,
                deleted_datetime: null
            });
            fetchEntraUsers();
        } catch (err: unknown) {
            const axiosError = err as { response?: { data?: { detail?: string } } };
            setError(axiosError.response?.data?.detail || 'Failed to restore user');
        }
    };

    const handleHardDelete = async (objectId: string) => {
        if (!confirm('Permanently delete this directory user? If provisioned as an app user, they will be marked as disabled.')) return;

        try {
            await api.delete(`/auth/entra/users/${objectId}`);
            fetchEntraUsers();
        } catch (err: unknown) {
            const axiosError = err as { response?: { data?: { detail?: string } } };
            setError(axiosError.response?.data?.detail || 'Failed to delete directory user');
        }
    };

    const getStatusBadge = (entraUser: EntraUser) => {
        if (entraUser.in_recycle_bin) {
            return (
                <span className="px-2 py-1 text-xs rounded-full bg-orange-100 text-orange-800">
                    In Recycle Bin
                </span>
            );
        }
        if (!entraUser.account_enabled) {
            return (
                <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                    Disabled
                </span>
            );
        }
        return (
            <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                Active
            </span>
        );
    };

    if (loading) {
        return <div className="flex items-center justify-center h-64">Loading...</div>;
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h3 className="text-lg font-semibold">Entra Directory</h3>
                    <p className="text-sm text-gray-500">
                        Mock Microsoft Entra ID directory for testing/demo
                    </p>
                </div>
                {userIsAdmin && (
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + Add Directory User
                    </button>
                )}
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {showForm && userIsAdmin && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingUser ? 'Edit Directory User' : 'Create Directory User'}
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="display_name" className="block text-sm font-medium mb-2">
                                    Display Name *
                                </label>
                                <input
                                    id="display_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.display_name}
                                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="mail" className="block text-sm font-medium mb-2">
                                    Email *
                                </label>
                                <input
                                    id="mail"
                                    type="email"
                                    className="input-field"
                                    value={formData.mail}
                                    onChange={(e) => setFormData({ ...formData, mail: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="user_principal_name" className="block text-sm font-medium mb-2">
                                    User Principal Name *
                                </label>
                                <input
                                    id="user_principal_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.user_principal_name}
                                    onChange={(e) => setFormData({ ...formData, user_principal_name: e.target.value })}
                                    placeholder="user@company.onmicrosoft.com"
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="given_name" className="block text-sm font-medium mb-2">
                                    First Name
                                </label>
                                <input
                                    id="given_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.given_name}
                                    onChange={(e) => setFormData({ ...formData, given_name: e.target.value })}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="surname" className="block text-sm font-medium mb-2">
                                    Last Name
                                </label>
                                <input
                                    id="surname"
                                    type="text"
                                    className="input-field"
                                    value={formData.surname}
                                    onChange={(e) => setFormData({ ...formData, surname: e.target.value })}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="job_title" className="block text-sm font-medium mb-2">
                                    Job Title
                                </label>
                                <input
                                    id="job_title"
                                    type="text"
                                    className="input-field"
                                    value={formData.job_title}
                                    onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="department" className="block text-sm font-medium mb-2">
                                    Department
                                </label>
                                <input
                                    id="department"
                                    type="text"
                                    className="input-field"
                                    value={formData.department}
                                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="office_location" className="block text-sm font-medium mb-2">
                                    Office Location
                                </label>
                                <input
                                    id="office_location"
                                    type="text"
                                    className="input-field"
                                    value={formData.office_location}
                                    onChange={(e) => setFormData({ ...formData, office_location: e.target.value })}
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="mobile_phone" className="block text-sm font-medium mb-2">
                                    Mobile Phone
                                </label>
                                <input
                                    id="mobile_phone"
                                    type="text"
                                    className="input-field"
                                    value={formData.mobile_phone}
                                    onChange={(e) => setFormData({ ...formData, mobile_phone: e.target.value })}
                                />
                            </div>
                            <div className="mb-4 flex items-center">
                                <input
                                    id="account_enabled"
                                    type="checkbox"
                                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                                    checked={formData.account_enabled}
                                    onChange={(e) => setFormData({ ...formData, account_enabled: e.target.checked })}
                                />
                                <label htmlFor="account_enabled" className="ml-2 text-sm font-medium">
                                    Account Enabled
                                </label>
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
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('display_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Name
                                    {getSortIcon('display_name')}
                                </div>
                            </th>
                            <th
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('mail')}
                            >
                                <div className="flex items-center gap-2">
                                    Email
                                    {getSortIcon('mail')}
                                </div>
                            </th>
                            <th
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('job_title')}
                            >
                                <div className="flex items-center gap-2">
                                    Job Title
                                    {getSortIcon('job_title')}
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
                                onClick={() => requestSort('in_recycle_bin')}
                            >
                                <div className="flex items-center gap-2">
                                    Status
                                    {getSortIcon('in_recycle_bin')}
                                </div>
                            </th>
                            {userIsAdmin && (
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            )}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={userIsAdmin ? 6 : 5} className="px-4 py-2 text-center text-gray-500">
                                    No directory users. Click "Add Directory User" to create one.
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((entraUser) => (
                                <tr key={entraUser.object_id} className={entraUser.in_recycle_bin ? 'bg-orange-50' : ''}>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <div className="font-medium">{entraUser.display_name}</div>
                                        <div className="text-xs text-gray-500">{entraUser.user_principal_name}</div>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                        {entraUser.mail}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                        {entraUser.job_title || '-'}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                        {entraUser.department || '-'}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        {getStatusBadge(entraUser)}
                                        {entraUser.deleted_datetime && (
                                            <div className="text-xs text-gray-500 mt-1">
                                                Deleted: {entraUser.deleted_datetime.split('T')[0]}
                                            </div>
                                        )}
                                    </td>
                                    {userIsAdmin && (
                                        <td className="px-4 py-2 whitespace-nowrap">
                                            {entraUser.in_recycle_bin ? (
                                                <>
                                                    <button
                                                        onClick={() => handleRestoreFromRecycleBin(entraUser.object_id)}
                                                        className="text-green-600 hover:text-green-800 text-sm mr-3"
                                                    >
                                                        Restore
                                                    </button>
                                                    <button
                                                        onClick={() => handleHardDelete(entraUser.object_id)}
                                                        className="text-red-600 hover:text-red-800 text-sm"
                                                    >
                                                        Permanently Delete
                                                    </button>
                                                </>
                                            ) : (
                                                <>
                                                    <button
                                                        onClick={() => handleEdit(entraUser)}
                                                        className="text-blue-600 hover:text-blue-800 text-sm mr-3"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleMoveToRecycleBin(entraUser.object_id)}
                                                        className="text-orange-600 hover:text-orange-800 text-sm mr-3"
                                                    >
                                                        Soft Delete
                                                    </button>
                                                    <button
                                                        onClick={() => handleHardDelete(entraUser.object_id)}
                                                        className="text-red-600 hover:text-red-800 text-sm"
                                                    >
                                                        Hard Delete
                                                    </button>
                                                </>
                                            )}
                                        </td>
                                    )}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default EntraDirectoryContent;

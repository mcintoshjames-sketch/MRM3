import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { isAdmin } from '../utils/roleUtils';

interface ApproverRole {
    role_id: number;
    role_name: string;
    description: string | null;
    is_active: boolean;
    rules_count?: number;
    created_at: string;
    updated_at: string;
}

export default function ApproverRolesPage() {
    const { user } = useAuth();
    const isAdminUser = isAdmin(user);
    const [roles, setRoles] = useState<ApproverRole[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingRole, setEditingRole] = useState<ApproverRole | null>(null);
    const [formData, setFormData] = useState({
        role_name: '',
        description: '',
        is_active: true
    });
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchRoles();
    }, []);

    const fetchRoles = async () => {
        try {
            const response = await api.get('/approver-roles/');
            setRoles(response.data);
        } catch (error) {
            console.error('Failed to fetch approver roles:', error);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({ role_name: '', description: '', is_active: true });
        setEditingRole(null);
        setShowForm(false);
        setError(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            if (editingRole) {
                await api.patch(`/approver-roles/${editingRole.role_id}`, formData);
            } else {
                await api.post('/approver-roles/', formData);
            }
            resetForm();
            fetchRoles();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save approver role');
        }
    };

    const handleEdit = (role: ApproverRole) => {
        setEditingRole(role);
        setFormData({
            role_name: role.role_name,
            description: role.description || '',
            is_active: role.is_active
        });
        setShowForm(true);
    };

    const handleDeactivate = async (roleId: number) => {
        if (!confirm('Are you sure you want to deactivate this approver role? This will prevent it from being used in new rules.')) return;

        try {
            await api.delete(`/approver-roles/${roleId}`);
            fetchRoles();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to deactivate approver role');
        }
    };

    // Only admins can access this page
    if (user && !isAdminUser) {
        return (
            <Layout>
                <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-800">Access Denied</h2>
                    <p className="text-gray-600 mt-2">Only administrators can manage approver roles.</p>
                </div>
            </Layout>
        );
    }

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
                <div>
                    <h2 className="text-2xl font-bold">Approver Roles</h2>
                    <p className="text-gray-600 text-sm mt-1">
                        Manage roles/committees that can approve model use
                    </p>
                </div>
                <button onClick={() => setShowForm(true)} className="btn-primary">
                    + Add Approver Role
                </button>
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingRole ? 'Edit Approver Role' : 'Create New Approver Role'}
                    </h3>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="mb-4">
                            <label htmlFor="role_name" className="block text-sm font-medium mb-2">
                                Role Name *
                            </label>
                            <input
                                id="role_name"
                                type="text"
                                className="input-field"
                                value={formData.role_name}
                                onChange={(e) => setFormData({ ...formData, role_name: e.target.value })}
                                placeholder="e.g., US Model Risk Management Committee"
                                maxLength={200}
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Unique name for this approver role or committee
                            </p>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="description" className="block text-sm font-medium mb-2">
                                Description
                            </label>
                            <textarea
                                id="description"
                                className="input-field"
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Optional description of this role's responsibilities"
                            />
                        </div>

                        <div className="mb-4">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={formData.is_active}
                                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                    className="mr-2"
                                />
                                <span className="text-sm font-medium">Active</span>
                            </label>
                            <p className="text-xs text-gray-500 mt-1">
                                Inactive roles cannot be used in new additional approval rules
                            </p>
                        </div>

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">
                                {editingRole ? 'Update Role' : 'Create Role'}
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
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Role Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Description
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Rules Using
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Status
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {roles.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                                    No approver roles defined. Click "Add Approver Role" to create one.
                                </td>
                            </tr>
                        ) : (
                            roles.map((role) => (
                                <tr key={role.role_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="text-sm font-medium text-gray-900">
                                            {role.role_name}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-600">
                                            {role.description || '-'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-900">
                                            {role.rules_count || 0}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span
                                            className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                role.is_active
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-gray-100 text-gray-800'
                                            }`}
                                        >
                                            {role.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right text-sm font-medium">
                                        <button
                                            onClick={() => handleEdit(role)}
                                            className="text-blue-600 hover:text-blue-800 mr-3"
                                        >
                                            Edit
                                        </button>
                                        {role.is_active && (
                                            <button
                                                onClick={() => handleDeactivate(role.role_id)}
                                                className="text-red-600 hover:text-red-800"
                                            >
                                                Deactivate
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Layout>
    );
}

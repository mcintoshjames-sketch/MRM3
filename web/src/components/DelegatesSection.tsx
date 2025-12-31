import React, { useState, useEffect } from 'react';
import { delegatesApi, ModelDelegate } from '../api/delegates';
import { usersApi, User } from '../api/users';
import { useAuth } from '../contexts/AuthContext';
import { isAdminOrValidator } from '../utils/roleUtils';

interface DelegatesSectionProps {
    modelId: number;
    modelOwnerId: number;
    currentUserId: number;
}

const DelegatesSection: React.FC<DelegatesSectionProps> = ({ modelId, modelOwnerId, currentUserId }) => {
    const { user } = useAuth();
    const [delegates, setDelegates] = useState<ModelDelegate[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddForm, setShowAddForm] = useState(false);
    const [formData, setFormData] = useState({
        user_id: 0,
        can_submit_changes: true,
        can_manage_regional: true,
    });
    const [error, setError] = useState<string | null>(null);
    const [userSearch, setUserSearch] = useState('');
    const [selectedUser, setSelectedUser] = useState<User | null>(null);

    // Admins, validators, and model owners can manage delegates
    const canManageDelegates = currentUserId === modelOwnerId || isAdminOrValidator(user);

    const loadDelegates = async () => {
        try {
            setLoading(true);
            const data = await delegatesApi.listDelegates(modelId, false);
            setDelegates(data);
            setError(null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load delegates');
        } finally {
            setLoading(false);
        }
    };

    const loadUsers = async () => {
        try {
            const data = await usersApi.listUsers();
            setUsers(data);
        } catch (err) {
            console.error('Failed to load users:', err);
        }
    };

    useEffect(() => {
        loadDelegates();
        loadUsers();
    }, [modelId]);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedUser) {
            alert('Please select a user');
            return;
        }

        try {
            await delegatesApi.createDelegate(modelId, {
                user_id: selectedUser.user_id,
                can_submit_changes: formData.can_submit_changes,
                can_manage_regional: formData.can_manage_regional,
            });
            setShowAddForm(false);
            setFormData({ user_id: 0, can_submit_changes: true, can_manage_regional: true });
            setSelectedUser(null);
            setUserSearch('');
            loadDelegates();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to add delegate');
        }
    };

    const filteredUsers = users
        .filter(u => u.user_id !== modelOwnerId)
        .filter(u => {
            if (!userSearch) return true;
            const search = userSearch.toLowerCase();
            return (
                u.full_name.toLowerCase().includes(search) ||
                u.email.toLowerCase().includes(search)
            );
        });

    const handleRevoke = async (delegateId: number) => {
        if (!confirm('Revoke this delegation?')) return;
        try {
            await delegatesApi.revokeDelegate(delegateId);
            loadDelegates();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to revoke delegate');
        }
    };

    if (loading) return <div className="p-4">Loading delegates...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Model Delegates</h3>
                {canManageDelegates && !showAddForm && (
                    <button
                        onClick={() => setShowAddForm(true)}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Add Delegate
                    </button>
                )}
            </div>

            {!canManageDelegates && (
                <p className="text-sm text-gray-500 mb-4">Only the model owner, validators, or administrators can manage delegates</p>
            )}

            {showAddForm && (
                <form onSubmit={handleAdd} className="mb-6 p-4 border border-gray-300 rounded bg-gray-50">
                    <h4 className="font-medium mb-3">Add New Delegate</h4>
                    <div className="mb-3">
                        <label className="block text-sm font-medium text-gray-700 mb-1">User *</label>
                        {selectedUser ? (
                            <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded">
                                <div>
                                    <div className="font-medium">{selectedUser.full_name}</div>
                                    <div className="text-sm text-gray-600">{selectedUser.email}</div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setSelectedUser(null)}
                                    className="text-red-600 hover:text-red-800 text-sm"
                                >
                                    Change
                                </button>
                            </div>
                        ) : (
                            <>
                                <input
                                    type="text"
                                    value={userSearch}
                                    onChange={(e) => setUserSearch(e.target.value)}
                                    placeholder="Search by name or email..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2"
                                />
                                <div className="max-h-48 overflow-y-auto border border-gray-300 rounded bg-white">
                                    {filteredUsers.length === 0 ? (
                                        <div className="p-3 text-sm text-gray-500">
                                            {userSearch ? 'No users found' : 'Start typing to search users'}
                                        </div>
                                    ) : (
                                        filteredUsers.slice(0, 10).map((u) => (
                                            <button
                                                key={u.user_id}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedUser(u);
                                                    setUserSearch('');
                                                }}
                                                className="w-full text-left p-3 hover:bg-gray-50 border-b border-gray-200 last:border-b-0"
                                            >
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-gray-600">{u.email}</div>
                                            </button>
                                        ))
                                    )}
                                    {filteredUsers.length > 10 && (
                                        <div className="p-2 text-xs text-gray-500 text-center bg-gray-50">
                                            {filteredUsers.length - 10} more users... Keep typing to narrow results
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                    <div className="mb-3">
                        <label className="flex items-center">
                            <input
                                type="checkbox"
                                checked={formData.can_submit_changes}
                                onChange={(e) => setFormData({ ...formData, can_submit_changes: e.target.checked })}
                                className="mr-2"
                            />
                            <span className="text-sm font-medium">Can submit model changes (create versions)</span>
                        </label>
                    </div>
                    <div className="mb-3">
                        <label className="flex items-center">
                            <input
                                type="checkbox"
                                checked={formData.can_manage_regional}
                                onChange={(e) => setFormData({ ...formData, can_manage_regional: e.target.checked })}
                                className="mr-2"
                            />
                            <span className="text-sm font-medium">Can manage regional configurations</span>
                        </label>
                    </div>
                    <div className="flex gap-2">
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Add
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setShowAddForm(false);
                                setFormData({ user_id: 0, can_submit_changes: true, can_manage_regional: true });
                                setSelectedUser(null);
                                setUserSearch('');
                            }}
                            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            )}

            {delegates.length === 0 ? (
                <p className="text-gray-500 text-sm">No delegates assigned</p>
            ) : (
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Permissions</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Delegated By</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                            {canManageDelegates && (
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            )}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {delegates.map((delegate) => (
                            <tr key={delegate.delegate_id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm">
                                    <div className="font-medium">{delegate.user_name}</div>
                                    <div className="text-xs text-gray-500">{delegate.user_email}</div>
                                </td>
                                <td className="px-4 py-3 text-sm">
                                    <div className="flex flex-col gap-1">
                                        {delegate.can_submit_changes && (
                                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded inline-block w-fit">
                                                Submit Changes
                                            </span>
                                        )}
                                        {delegate.can_manage_regional && (
                                            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded inline-block w-fit">
                                                Manage Regional
                                            </span>
                                        )}
                                    </div>
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600">{delegate.delegated_by_name}</td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                    {delegate.delegated_at.split('T')[0]}
                                </td>
                                {canManageDelegates && (
                                    <td className="px-4 py-3 text-sm">
                                        <button
                                            onClick={() => handleRevoke(delegate.delegate_id)}
                                            className="text-red-600 hover:text-red-800 font-medium"
                                        >
                                            Revoke
                                        </button>
                                    </td>
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default DelegatesSection;

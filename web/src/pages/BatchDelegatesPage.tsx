import React, { useState, useEffect } from 'react';
import { delegatesApi, BatchDelegateResponse } from '../api/delegates';
import { usersApi, User } from '../api/users';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function BatchDelegatesPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<BatchDelegateResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [lastOperation, setLastOperation] = useState<{
        targetUserName: string;
        delegateUserName: string;
        role: string;
        canSubmitChanges: boolean;
        canManageRegional: boolean;
        replaceExisting: boolean;
    } | null>(null);

    // Form state
    const [targetUserSearch, setTargetUserSearch] = useState('');
    const [selectedTargetUser, setSelectedTargetUser] = useState<User | null>(null);
    const [role, setRole] = useState<'owner' | 'developer'>('owner');
    const [delegateUserSearch, setDelegateUserSearch] = useState('');
    const [selectedDelegateUser, setSelectedDelegateUser] = useState<User | null>(null);
    const [canSubmitChanges, setCanSubmitChanges] = useState(true);
    const [canManageRegional, setCanManageRegional] = useState(true);
    const [replaceExisting, setReplaceExisting] = useState(false);

    // Redirect if not admin
    useEffect(() => {
        if (user && user.role !== 'Admin') {
            navigate('/models');
        }
    }, [user, navigate]);

    // Load users
    useEffect(() => {
        const loadUsers = async () => {
            try {
                const data = await usersApi.listUsers();
                setUsers(data);
            } catch (err) {
                console.error('Failed to load users:', err);
            }
        };
        loadUsers();
    }, []);

    const filteredTargetUsers = users.filter(u => {
        if (!targetUserSearch) return true;
        const search = targetUserSearch.toLowerCase();
        return (
            u.full_name.toLowerCase().includes(search) ||
            u.email.toLowerCase().includes(search)
        );
    });

    const filteredDelegateUsers = users.filter(u => {
        // Cannot delegate to same user
        if (selectedTargetUser && u.user_id === selectedTargetUser.user_id) return false;
        if (!delegateUserSearch) return true;
        const search = delegateUserSearch.toLowerCase();
        return (
            u.full_name.toLowerCase().includes(search) ||
            u.email.toLowerCase().includes(search)
        );
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedTargetUser || !selectedDelegateUser) {
            setError('Please select both target user and delegate user');
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const response = await delegatesApi.batchAddDelegates({
                target_user_id: selectedTargetUser.user_id,
                role: role,
                delegate_user_id: selectedDelegateUser.user_id,
                can_submit_changes: canSubmitChanges,
                can_manage_regional: canManageRegional,
                replace_existing: replaceExisting,
            });
            setResult(response);
            // Store operation metadata for CSV export
            setLastOperation({
                targetUserName: selectedTargetUser.full_name,
                delegateUserName: selectedDelegateUser.full_name,
                role: role,
                canSubmitChanges: canSubmitChanges,
                canManageRegional: canManageRegional,
                replaceExisting: replaceExisting,
            });
            // Reset form
            setSelectedTargetUser(null);
            setSelectedDelegateUser(null);
            setTargetUserSearch('');
            setDelegateUserSearch('');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to perform batch delegate operation');
        } finally {
            setLoading(false);
        }
    };

    const downloadCSV = () => {
        if (!result || !lastOperation) return;

        const rows = [
            ['Batch Delegate Operation Summary'],
            [''],
            ['Target User:', lastOperation.targetUserName],
            ['Role:', lastOperation.role === 'owner' ? 'Models Owned' : 'Models Developed'],
            ['Delegate User:', lastOperation.delegateUserName],
            ['Can Submit Changes:', lastOperation.canSubmitChanges ? 'Yes' : 'No'],
            ['Can Manage Regional:', lastOperation.canManageRegional ? 'Yes' : 'No'],
            ['Replace Existing Delegates:', lastOperation.replaceExisting ? 'Yes' : 'No'],
            [''],
            ['Results:'],
            ['Models Affected:', result.models_affected.toString()],
            ['Delegations Created:', result.delegations_created.toString()],
            ['Delegations Updated:', result.delegations_updated.toString()],
            ...(result.delegations_revoked > 0 ? [['Delegations Revoked:', result.delegations_revoked.toString()]] : []),
            [''],
            ['Affected Models:'],
            ['Model ID', 'Model Name', 'Action'],
            ...result.model_details.map(detail => [
                detail.model_id.toString(),
                detail.model_name,
                detail.action.charAt(0).toUpperCase() + detail.action.slice(1)
            ])
        ];

        const csvContent = rows.map(row => row.join(',')).join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `batch_delegates_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    };

    if (user?.role !== 'Admin') {
        return null; // Will redirect
    }

    return (
        <Layout>
            <div className="max-w-4xl mx-auto">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold">Batch Delegate Management</h1>
                    <p className="text-gray-600 mt-2">
                        Add or update a delegate for all models owned or developed by a specific user
                    </p>
                </div>

                {error && (
                    <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                        {error}
                    </div>
                )}

                {result && (
                    <div className="mb-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
                        <div className="flex justify-between items-start mb-2">
                            <h3 className="font-bold">Batch Operation Successful</h3>
                            <button
                                onClick={downloadCSV}
                                className="px-3 py-1 bg-green-700 text-white rounded hover:bg-green-800 text-sm"
                            >
                                Download CSV Summary
                            </button>
                        </div>
                        <ul className="list-disc list-inside space-y-1">
                            <li>Models affected: {result.models_affected}</li>
                            <li>New delegations created: {result.delegations_created}</li>
                            <li>Existing delegations updated: {result.delegations_updated}</li>
                        </ul>
                        {result.model_ids.length > 0 && (
                            <details className="mt-3">
                                <summary className="cursor-pointer font-medium">View affected model IDs</summary>
                                <div className="mt-2 text-sm">
                                    {result.model_ids.join(', ')}
                                </div>
                            </details>
                        )}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-6">
                    {/* Target User Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Target User (Owner/Developer) *
                        </label>
                        <p className="text-sm text-gray-500 mb-2">
                            Select the user whose models you want to add delegates to
                        </p>
                        {selectedTargetUser ? (
                            <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded">
                                <div>
                                    <div className="font-medium">{selectedTargetUser.full_name}</div>
                                    <div className="text-sm text-gray-600">{selectedTargetUser.email}</div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setSelectedTargetUser(null)}
                                    className="text-red-600 hover:text-red-800 text-sm"
                                >
                                    Change
                                </button>
                            </div>
                        ) : (
                            <>
                                <input
                                    type="text"
                                    value={targetUserSearch}
                                    onChange={(e) => setTargetUserSearch(e.target.value)}
                                    placeholder="Search by name or email..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2"
                                />
                                <div className="max-h-48 overflow-y-auto border border-gray-300 rounded bg-white">
                                    {filteredTargetUsers.length === 0 ? (
                                        <div className="p-3 text-sm text-gray-500">
                                            {targetUserSearch ? 'No users found' : 'Start typing to search users'}
                                        </div>
                                    ) : (
                                        filteredTargetUsers.slice(0, 10).map((u) => (
                                            <button
                                                key={u.user_id}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedTargetUser(u);
                                                    setTargetUserSearch('');
                                                }}
                                                className="w-full text-left p-3 hover:bg-gray-50 border-b border-gray-200 last:border-b-0"
                                            >
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-gray-600">{u.email}</div>
                                            </button>
                                        ))
                                    )}
                                    {filteredTargetUsers.length > 10 && (
                                        <div className="p-2 text-xs text-gray-500 text-center bg-gray-50">
                                            {filteredTargetUsers.length - 10} more users... Keep typing to narrow results
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Role Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Role *
                        </label>
                        <p className="text-sm text-gray-500 mb-2">
                            Select whether to target models where the user is owner or developer
                        </p>
                        <div className="space-y-2">
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    value="owner"
                                    checked={role === 'owner'}
                                    onChange={(e) => setRole(e.target.value as 'owner' | 'developer')}
                                    className="mr-2"
                                />
                                <span>Models where user is <strong>Owner</strong></span>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    value="developer"
                                    checked={role === 'developer'}
                                    onChange={(e) => setRole(e.target.value as 'owner' | 'developer')}
                                    className="mr-2"
                                />
                                <span>Models where user is <strong>Developer</strong></span>
                            </label>
                        </div>
                    </div>

                    {/* Delegate User Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Delegate User *
                        </label>
                        <p className="text-sm text-gray-500 mb-2">
                            Select the user to grant delegation permissions to
                        </p>
                        {selectedDelegateUser ? (
                            <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded">
                                <div>
                                    <div className="font-medium">{selectedDelegateUser.full_name}</div>
                                    <div className="text-sm text-gray-600">{selectedDelegateUser.email}</div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setSelectedDelegateUser(null)}
                                    className="text-red-600 hover:text-red-800 text-sm"
                                >
                                    Change
                                </button>
                            </div>
                        ) : (
                            <>
                                <input
                                    type="text"
                                    value={delegateUserSearch}
                                    onChange={(e) => setDelegateUserSearch(e.target.value)}
                                    placeholder="Search by name or email..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2"
                                />
                                <div className="max-h-48 overflow-y-auto border border-gray-300 rounded bg-white">
                                    {filteredDelegateUsers.length === 0 ? (
                                        <div className="p-3 text-sm text-gray-500">
                                            {delegateUserSearch ? 'No users found' : 'Start typing to search users'}
                                        </div>
                                    ) : (
                                        filteredDelegateUsers.slice(0, 10).map((u) => (
                                            <button
                                                key={u.user_id}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedDelegateUser(u);
                                                    setDelegateUserSearch('');
                                                }}
                                                className="w-full text-left p-3 hover:bg-gray-50 border-b border-gray-200 last:border-b-0"
                                            >
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-gray-600">{u.email}</div>
                                            </button>
                                        ))
                                    )}
                                    {filteredDelegateUsers.length > 10 && (
                                        <div className="p-2 text-xs text-gray-500 text-center bg-gray-50">
                                            {filteredDelegateUsers.length - 10} more users... Keep typing to narrow results
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Permissions */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Permissions
                        </label>
                        <div className="space-y-2">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={canSubmitChanges}
                                    onChange={(e) => setCanSubmitChanges(e.target.checked)}
                                    className="mr-2"
                                />
                                <span className="text-sm">Can submit model changes (create versions)</span>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={canManageRegional}
                                    onChange={(e) => setCanManageRegional(e.target.checked)}
                                    className="mr-2"
                                />
                                <span className="text-sm">Can manage regional configurations</span>
                            </label>
                        </div>
                    </div>

                    {/* Replace Existing Option */}
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
                        <label className="flex items-start">
                            <input
                                type="checkbox"
                                checked={replaceExisting}
                                onChange={(e) => setReplaceExisting(e.target.checked)}
                                className="mr-2 mt-0.5"
                            />
                            <div>
                                <span className="text-sm font-medium text-gray-900">Replace all existing delegates</span>
                                <p className="text-xs text-gray-600 mt-1">
                                    If checked, all other delegates for each model will be revoked, leaving only the selected delegate user.
                                    If unchecked, the selected delegate will be added alongside existing delegates.
                                </p>
                            </div>
                        </label>
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-end">
                        <button
                            type="submit"
                            disabled={loading || !selectedTargetUser || !selectedDelegateUser}
                            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                        >
                            {loading ? 'Processing...' : 'Apply Batch Delegation'}
                        </button>
                    </div>
                </form>
            </div>
        </Layout>
    );
}

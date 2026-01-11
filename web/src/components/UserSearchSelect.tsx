import { useEffect, useMemo, useState } from 'react';
import api from '../api/client';

export interface UserSearchOption {
    user_id: number;
    email: string;
    full_name: string;
    role?: string;
}

interface UserSearchSelectProps {
    value: number | null;
    onChange: (userId: number | null, user?: UserSearchOption) => void;
    users: UserSearchOption[];
    setUsers: React.Dispatch<React.SetStateAction<UserSearchOption[]>>;
    placeholder: string;
    label?: string;
    inputId?: string;
    required?: boolean;
    disabled?: boolean;
    excludeUserIds?: number[];
    helperText?: string;
}

const mergeUsers = (existing: UserSearchOption[], incoming: UserSearchOption[]) => {
    const map = new Map<number, UserSearchOption>();
    existing.forEach((user) => map.set(user.user_id, user));
    incoming.forEach((user) => map.set(user.user_id, user));
    return Array.from(map.values()).sort((a, b) => a.full_name.localeCompare(b.full_name));
};

export default function UserSearchSelect({
    value,
    onChange,
    users,
    setUsers,
    placeholder,
    label,
    inputId,
    required,
    disabled,
    excludeUserIds,
    helperText
}: UserSearchSelectProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [lookupLoading, setLookupLoading] = useState(false);
    const [lookupError, setLookupError] = useState<string | null>(null);

    const selectedUser = useMemo(
        () => users.find((user) => user.user_id === value) || null,
        [users, value]
    );

    useEffect(() => {
        if (value === null) {
            setSearchTerm('');
            return;
        }
        if (selectedUser) {
            setSearchTerm(selectedUser.full_name);
        }
    }, [selectedUser, value]);

    useEffect(() => {
        if (lookupError) {
            setLookupError(null);
        }
    }, [searchTerm]);

    const filteredUsers = useMemo(() => {
        const normalized = searchTerm.trim().toLowerCase();
        if (!normalized) return [];
        const excluded = new Set(excludeUserIds || []);
        return users.filter((user) =>
            !excluded.has(user.user_id) &&
            (user.full_name.toLowerCase().includes(normalized) ||
                user.email.toLowerCase().includes(normalized))
        ).slice(0, 50);
    }, [searchTerm, users, excludeUserIds]);

    const handleSearchByEmail = async () => {
        const trimmed = searchTerm.trim();
        if (!trimmed) {
            setLookupError('Enter an email to search.');
            return;
        }
        setLookupLoading(true);
        setLookupError(null);
        try {
            const response = await api.get('/users/search', { params: { email: trimmed } });
            const results = (response.data || []).map((item: UserSearchOption) => ({
                user_id: item.user_id,
                email: item.email,
                full_name: item.full_name,
                role: item.role ?? 'User'
            }));
            if (results.length === 0) {
                setLookupError('No users found for that email.');
                return;
            }
            setUsers((prev) => mergeUsers(prev, results));
            setShowDropdown(true);
        } catch (error: any) {
            console.error('Failed to search users:', error);
            setLookupError(error.response?.data?.detail || 'Unable to search users.');
        } finally {
            setLookupLoading(false);
        }
    };

    return (
        <div>
            {label && (
                <label htmlFor={inputId} className="block text-sm font-medium mb-2">
                    {label}
                </label>
            )}
            <div className="relative">
                <input
                    id={inputId}
                    type="text"
                    placeholder={placeholder}
                    value={searchTerm}
                    onChange={(e) => {
                        const nextValue = e.target.value;
                        setSearchTerm(nextValue);
                        setShowDropdown(true);
                        if (value && selectedUser) {
                            if (nextValue !== selectedUser.full_name && nextValue !== selectedUser.email) {
                                onChange(null);
                            }
                        }
                        if (!nextValue.trim()) {
                            onChange(null);
                        }
                    }}
                    onFocus={() => setShowDropdown(true)}
                    className="input-field"
                    required={required}
                    disabled={disabled}
                />
                {showDropdown && searchTerm.length > 0 && filteredUsers.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                        {filteredUsers.map((user) => (
                            <div
                                key={user.user_id}
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                onClick={() => {
                                    onChange(user.user_id, user);
                                    setSearchTerm(user.full_name);
                                    setShowDropdown(false);
                                }}
                            >
                                <div className="font-medium">{user.full_name}</div>
                                <div className="text-xs text-gray-500">{user.email}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            {showDropdown && searchTerm.length > 0 && filteredUsers.length === 0 && (
                <p className="mt-1 text-sm text-gray-500">No users found. Use Search by Email below.</p>
            )}
            {selectedUser && (
                <p className="mt-1 text-sm text-green-600">Selected: {selectedUser.full_name}</p>
            )}
            <div className="mt-2 flex items-center gap-2">
                <button
                    type="button"
                    onClick={handleSearchByEmail}
                    className="btn-secondary px-3 py-1 text-xs"
                    disabled={lookupLoading || !searchTerm.trim()}
                >
                    {lookupLoading ? 'Searching...' : 'Search by Email'}
                </button>
                {lookupError && (
                    <span className="text-xs text-red-600">{lookupError}</span>
                )}
            </div>
            {helperText && (
                <p className="mt-1 text-xs text-gray-500">{helperText}</p>
            )}
        </div>
    );
}

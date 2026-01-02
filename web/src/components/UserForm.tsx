import { useEffect, useState } from 'react';
import api from '../api/client';
import { Region } from '../api/regions';
import { LOBUnit } from '../api/lob';
import { getUserRoleCode } from '../utils/roleUtils';

interface RoleOption {
    role_id: number;
    role_code: string;
    display_name: string;
    is_active: boolean;
}

interface LOBBrief {
    lob_id: number;
    code: string;
    name: string;
    level: number;
    full_path: string;
}

interface UserLike {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    role_code?: string | null;
    regions?: Region[];
    lob_id: number | null;
    lob?: LOBBrief | null;
}

interface UserFormProps {
    editingUser: UserLike | null;
    regions: Region[];
    lobUnits: LOBUnit[];
    roleOptions: RoleOption[];
    onSaved: (user: UserLike) => void;
    onCancel: () => void;
}

const defaultFormData = {
    email: '',
    full_name: '',
    password: '',
    role_code: 'USER',
    region_ids: [] as number[],
    lob_id: null as number | null
};

export default function UserForm({
    editingUser,
    regions,
    lobUnits,
    roleOptions,
    onSaved,
    onCancel
}: UserFormProps) {
    const [formData, setFormData] = useState(defaultFormData);
    const [lobSearch, setLobSearch] = useState('');
    const [showLobDropdown, setShowLobDropdown] = useState(false);

    useEffect(() => {
        if (editingUser) {
            const editingRoleCode = getUserRoleCode(editingUser) ?? 'USER';
            setFormData({
                email: editingUser.email,
                full_name: editingUser.full_name,
                password: '',
                role_code: editingRoleCode,
                region_ids: editingUser.regions?.map(r => r.region_id) || [],
                lob_id: editingUser.lob_id
            });

            if (editingUser.lob_id) {
                const lobUnit = lobUnits.find(l => l.lob_id === editingUser.lob_id);
                if (lobUnit) {
                    setLobSearch(`[${lobUnit.org_unit}] ${lobUnit.full_path}`);
                } else if (editingUser.lob) {
                    setLobSearch(editingUser.lob.full_path);
                } else {
                    setLobSearch('');
                }
            } else {
                setLobSearch('');
            }
        } else {
            setFormData(defaultFormData);
            setLobSearch('');
        }
        setShowLobDropdown(false);
    }, [editingUser, lobUnits]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!editingUser && !formData.lob_id) {
            alert('Line of Business (LOB) is required for all users');
            return;
        }

        try {
            if (editingUser) {
                const updatePayload: Record<string, any> = {};
                if (formData.email !== editingUser.email) updatePayload.email = formData.email;
                if (formData.full_name !== editingUser.full_name) updatePayload.full_name = formData.full_name;
                const editingRoleCode = getUserRoleCode(editingUser) ?? 'USER';
                if (formData.role_code !== editingRoleCode) {
                    updatePayload.role_code = formData.role_code;
                }
                if (formData.password) updatePayload.password = formData.password;

                if (formData.role_code === 'REGIONAL_APPROVER' || editingRoleCode === 'REGIONAL_APPROVER') {
                    updatePayload.region_ids = formData.region_ids;
                }

                if (formData.lob_id !== editingUser.lob_id) {
                    updatePayload.lob_id = formData.lob_id;
                }

                const response = await api.patch(`/auth/users/${editingUser.user_id}`, updatePayload);
                onSaved(response.data);
            } else {
                const response = await api.post('/auth/register', formData);
                onSaved(response.data);
            }
            onCancel();
        } catch (error) {
            console.error('Failed to save user:', error);
        }
    };

    return (
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
                            value={formData.role_code}
                            onChange={(e) => setFormData({ ...formData, role_code: e.target.value, region_ids: [] })}
                        >
                            {roleOptions.map((role) => (
                                <option key={role.role_code} value={role.role_code}>
                                    {role.display_name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

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
                                Selected: [{lobUnits.find(l => l.lob_id === formData.lob_id)?.org_unit}] {lobUnits.find(l => l.lob_id === formData.lob_id)?.full_path || 'Unknown'}
                            </p>
                        )}
                    </div>
                </div>

                {formData.role_code === 'REGIONAL_APPROVER' && (
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
                    <button type="button" onClick={onCancel} className="btn-secondary">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}

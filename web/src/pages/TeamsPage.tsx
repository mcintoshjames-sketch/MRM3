import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import TeamLOBAssignment from '../components/TeamLOBAssignment';
import { useAuth } from '../contexts/AuthContext';
import { canManageTeams } from '../utils/roleUtils';
import { useTableSort } from '../hooks/useTableSort';
import {
    getTeams,
    getTeam,
    createTeam,
    updateTeam,
    deleteTeam,
    Team,
    TeamDetail
} from '../api/teams';

const TeamsPage: React.FC = () => {
    const { user } = useAuth();
    const canManage = canManageTeams(user);
    const [teams, setTeams] = useState<Team[]>([]);
    const [selectedTeam, setSelectedTeam] = useState<TeamDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [editingTeam, setEditingTeam] = useState<Team | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        is_active: true
    });
    const { sortedData: sortedTeams, requestSort, getSortIcon } = useTableSort<Team>(teams, 'name');

    const fetchTeams = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await getTeams();
            setTeams(response.data);
        } catch (err) {
            console.error('Failed to load teams:', err);
            setError('Failed to load teams');
        } finally {
            setLoading(false);
        }
    };

    const fetchTeamDetail = async (teamId: number) => {
        setLoadingDetail(true);
        try {
            const response = await getTeam(teamId);
            setSelectedTeam(response.data);
        } catch (err) {
            console.error('Failed to load team:', err);
            setError('Failed to load team details');
        } finally {
            setLoadingDetail(false);
        }
    };

    useEffect(() => {
        fetchTeams();
    }, []);

    const resetForm = () => {
        setFormData({ name: '', description: '', is_active: true });
        setEditingTeam(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.name.trim()) {
            setError('Team name is required');
            return;
        }
        setError(null);
        try {
            if (editingTeam) {
                const editedTeamId = editingTeam.team_id;
                await updateTeam(editingTeam.team_id, {
                    name: formData.name.trim(),
                    description: formData.description.trim() || null,
                    is_active: formData.is_active
                });
                await fetchTeams();
                resetForm();
                setSelectedTeam(null);
                fetchTeamDetail(editedTeamId);
                return;
            } else {
                const response = await createTeam({
                    name: formData.name.trim(),
                    description: formData.description.trim() || null,
                    is_active: formData.is_active
                });
                const newTeamId = response.data.team_id;
                await fetchTeams();
                resetForm();
                setSelectedTeam(null);
                fetchTeamDetail(newTeamId);
                return;
            }
            await fetchTeams();
            resetForm();
        } catch (err: any) {
            const message = err?.response?.data?.detail || 'Failed to save team';
            setError(message);
        }
    };

    const handleEdit = (team: Team) => {
        setEditingTeam(team);
        setFormData({
            name: team.name,
            description: team.description || '',
            is_active: team.is_active
        });
        setShowForm(true);
    };

    const handleSelect = (team: Team) => {
        setSelectedTeam(null);
        fetchTeamDetail(team.team_id);
    };

    const handleDeactivate = async (teamId: number) => {
        if (!confirm('Deactivate this team? It will remain in reports as inactive.')) return;
        try {
            await deleteTeam(teamId);
            await fetchTeams();
            if (selectedTeam?.team_id === teamId) {
                setSelectedTeam(null);
            }
        } catch (err: any) {
            const message = err?.response?.data?.detail || 'Failed to deactivate team';
            setError(message);
        }
    };

    const handleExportCSV = () => {
        const lines: string[] = [];
        lines.push('Team Name,Description,Active,LOB Count,Model Count,Created,Updated');
        sortedTeams.forEach((team) => {
            const row = [
                team.name,
                team.description || '',
                team.is_active ? 'Yes' : 'No',
                team.lob_count,
                team.model_count,
                team.created_at?.split('T')[0] || '',
                team.updated_at?.split('T')[0] || ''
            ];
            lines.push(row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','));
        });
        const csvContent = lines.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `teams_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <Layout>
            <div className="space-y-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold text-gray-900">Teams</h1>
                        <p className="text-sm text-gray-500">Group LOB units for reporting and filter views by team.</p>
                    </div>
                    <div className="flex flex-wrap gap-2 w-full md:w-auto md:justify-end">
                        <button onClick={handleExportCSV} className="btn-secondary w-full sm:w-auto">
                            Export CSV
                        </button>
                        {canManage && (
                            <button onClick={() => setShowForm(true)} className="btn-primary w-full sm:w-auto">
                                + New Team
                            </button>
                        )}
                    </div>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 gap-6">
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b">
                            <h2 className="text-sm font-semibold text-gray-700">Teams</h2>
                        </div>
                        {loading ? (
                            <div className="p-4 text-sm text-gray-500">Loading teams...</div>
                        ) : teams.length === 0 ? (
                            <div className="p-4 text-sm text-gray-500">No teams yet.</div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200 text-sm">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th
                                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestSort('name')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Team
                                                    {getSortIcon('name')}
                                                </div>
                                            </th>
                                            <th
                                                className="hidden md:table-cell px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestSort('lob_count')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    LOBs
                                                    {getSortIcon('lob_count')}
                                                </div>
                                            </th>
                                            <th
                                                className="hidden md:table-cell px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestSort('model_count')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Models
                                                    {getSortIcon('model_count')}
                                                </div>
                                            </th>
                                            <th className="hidden md:table-cell px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                            <th className="hidden md:table-cell px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                    {sortedTeams.map((team) => (
                                        <tr
                                            key={team.team_id}
                                            className={`align-top ${
                                                selectedTeam?.team_id === team.team_id ? 'bg-blue-50' : 'hover:bg-gray-50'
                                            }`}
                                        >
                                                <td className="px-4 py-2 font-medium text-gray-900">
                                                    <div className="flex flex-col gap-2">
                                                        <span>{team.name}</span>
                                                        <div className="text-xs text-gray-500 md:hidden">
                                                            LOBs: {team.lob_count} • Models: {team.model_count}
                                                        </div>
                                                        <div className="flex flex-wrap items-center gap-2 md:hidden">
                                                            <span className={`px-2 py-0.5 rounded-full text-xs ${
                                                                team.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'
                                                            }`}>
                                                                {team.is_active ? 'Active' : 'Inactive'}
                                                            </span>
                                                            <button
                                                                onClick={() => handleSelect(team)}
                                                                className="text-blue-600 hover:text-blue-800 text-xs"
                                                            >
                                                                View
                                                            </button>
                                                            {canManage && (
                                                                <>
                                                                    <button
                                                                        onClick={() => handleEdit(team)}
                                                                        className="text-gray-600 hover:text-gray-800 text-xs"
                                                                    >
                                                                        Edit
                                                                    </button>
                                                                    <button
                                                                        onClick={() => handleDeactivate(team.team_id)}
                                                                        className="text-red-600 hover:text-red-800 text-xs"
                                                                    >
                                                                        Deactivate
                                                                    </button>
                                                                </>
                                                            )}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="hidden md:table-cell px-4 py-2">{team.lob_count}</td>
                                                <td className="hidden md:table-cell px-4 py-2">{team.model_count}</td>
                                                <td className="hidden md:table-cell px-4 py-2">
                                                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                                                        team.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'
                                                    }`}>
                                                        {team.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </td>
                                                <td className="hidden md:table-cell px-4 py-2 space-x-2">
                                                    <button
                                                        onClick={() => handleSelect(team)}
                                                        className="text-blue-600 hover:text-blue-800 text-xs"
                                                    >
                                                        View
                                                    </button>
                                                    {canManage && (
                                                        <>
                                                            <button
                                                                onClick={() => handleEdit(team)}
                                                                className="text-gray-600 hover:text-gray-800 text-xs"
                                                            >
                                                                Edit
                                                            </button>
                                                            <button
                                                                onClick={() => handleDeactivate(team.team_id)}
                                                                className="text-red-600 hover:text-red-800 text-xs"
                                                            >
                                                                Deactivate
                                                            </button>
                                                        </>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    <div className="bg-white rounded-lg shadow-md p-4">
                        {showForm && (
                            <form onSubmit={handleSubmit} className="mb-4 border-b pb-4">
                                <h2 className="text-sm font-semibold text-gray-700 mb-3">
                                    {editingTeam ? 'Edit Team' : 'Create Team'}
                                </h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
                                        <input
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            className="input-field"
                                            placeholder="Team name"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2 mt-6">
                                        <input
                                            type="checkbox"
                                            checked={formData.is_active}
                                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                            className="h-4 w-4 text-blue-600 rounded"
                                        />
                                        <span className="text-xs text-gray-600">Active</span>
                                    </div>
                                    <div className="md:col-span-2">
                                        <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
                                        <textarea
                                            value={formData.description}
                                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                            className="input-field h-24"
                                            placeholder="Optional description"
                                        />
                                    </div>
                                </div>
                                <div className="flex justify-end gap-2 mt-3">
                                    <button type="button" onClick={resetForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn-primary">
                                        {editingTeam ? 'Save Changes' : 'Create Team'}
                                    </button>
                                </div>
                            </form>
                        )}

                        {!selectedTeam ? (
                            <div className="text-sm text-gray-500">
                                Select a team to view details and manage LOB assignments.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-lg font-semibold text-gray-900">{selectedTeam.name}</h2>
                                        <p className="text-sm text-gray-500">
                                            {selectedTeam.description || 'No description provided.'}
                                        </p>
                                    </div>
                                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                                        selectedTeam.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'
                                    }`}>
                                        {selectedTeam.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>

                                <div className="grid grid-cols-3 gap-4">
                                    <div className="bg-gray-50 p-3 rounded">
                                        <div className="text-xs text-gray-500">Direct LOBs</div>
                                        <div className="text-lg font-semibold text-gray-800">{selectedTeam.lob_count}</div>
                                    </div>
                                    <div className="bg-gray-50 p-3 rounded">
                                        <div className="text-xs text-gray-500">Models</div>
                                        <div className="text-lg font-semibold text-gray-800">{selectedTeam.model_count}</div>
                                    </div>
                                    <div className="bg-gray-50 p-3 rounded">
                                        <div className="text-xs text-gray-500">Updated</div>
                                        <div className="text-lg font-semibold text-gray-800">
                                            {selectedTeam.updated_at?.split('T')[0] || '-'}
                                        </div>
                                    </div>
                                </div>

                                {loadingDetail ? (
                                    <div className="text-sm text-gray-500">Loading team details...</div>
                                ) : (
                                    <TeamLOBAssignment
                                        teamId={selectedTeam.team_id}
                                        teamName={selectedTeam.name}
                                        canManage={canManage}
                                        onAssignmentsUpdated={() => {
                                            fetchTeams();
                                            fetchTeamDetail(selectedTeam.team_id);
                                        }}
                                    />
                                )}

                                {selectedTeam.lob_units && selectedTeam.lob_units.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-700 mt-4">Direct LOB Assignments</h3>
                                        <div className="mt-2 space-y-2">
                                            {selectedTeam.lob_units.map((lob) => (
                                                <div key={lob.lob_id} className="flex items-center justify-between text-sm bg-gray-50 px-3 py-2 rounded">
                                                    <div>
                                                        <div className="font-medium text-gray-800">{lob.name}</div>
                                                        <div className="text-xs text-gray-500">
                                                            [{lob.org_unit}] {lob.full_path || ''}
                                                        </div>
                                                    </div>
                                                    {!lob.is_active && (
                                                        <span className="text-xs text-red-600">Inactive</span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default TeamsPage;

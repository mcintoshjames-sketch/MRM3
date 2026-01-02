import client from './client';

export interface Team {
    team_id: number;
    name: string;
    description?: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    lob_count: number;
    model_count: number;
}

export interface TeamCreate {
    name: string;
    description?: string | null;
    is_active?: boolean;
}

export interface TeamUpdate {
    name?: string;
    description?: string | null;
    is_active?: boolean;
}

export interface TeamLOB {
    lob_id: number;
    name: string;
    org_unit: string;
    level: number;
    parent_id: number | null;
    full_path?: string | null;
    is_active: boolean;
}

export interface TeamDetail extends Team {
    lob_units: TeamLOB[];
}

export const getTeams = () => client.get<Team[]>('/teams/');
export const getTeam = (id: number) => client.get<TeamDetail>(`/teams/${id}`);
export const createTeam = (data: TeamCreate) => client.post<Team>('/teams/', data);
export const updateTeam = (id: number, data: TeamUpdate) => client.patch<Team>(`/teams/${id}`, data);
export const deleteTeam = (id: number) => client.delete(`/teams/${id}`);
export const assignLOBToTeam = (teamId: number, lobId: number) =>
    client.post<TeamLOB>(`/teams/${teamId}/lobs`, { lob_id: lobId });
export const removeLOBFromTeam = (teamId: number, lobId: number) =>
    client.delete(`/teams/${teamId}/lobs/${lobId}`);

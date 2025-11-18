import api from './client';

export interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
}

export const usersApi = {
    // List all users
    listUsers: async (): Promise<User[]> => {
        const response = await api.get('/auth/users');
        return response.data;
    },

    // Get specific user
    getUser: async (userId: number): Promise<User> => {
        const response = await api.get(`/auth/users/${userId}`);
        return response.data;
    },
};

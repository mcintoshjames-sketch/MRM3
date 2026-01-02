import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import TeamsPage from './TeamsPage';

const mockGet = vi.fn();
const mockGetTeams = vi.fn();
const mockGetTeam = vi.fn();
const mockCreateTeam = vi.fn();
const mockUpdateTeam = vi.fn();
const mockDeleteTeam = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

vi.mock('../api/teams', () => ({
    getTeams: (...args: any[]) => mockGetTeams(...args),
    getTeam: (...args: any[]) => mockGetTeam(...args),
    createTeam: (...args: any[]) => mockCreateTeam(...args),
    updateTeam: (...args: any[]) => mockUpdateTeam(...args),
    deleteTeam: (...args: any[]) => mockDeleteTeam(...args),
}));

vi.mock('../components/TeamLOBAssignment', () => ({
    default: () => <div data-testid="lob-assignment" />,
}));

vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: {
            user_id: 1,
            email: 'admin@example.com',
            full_name: 'Admin User',
            role: 'Admin',
        },
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
    }),
}));

const sampleTeams = [
    {
        team_id: 1,
        name: 'Credit Risk Team',
        description: 'Credit team',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        lob_count: 2,
        model_count: 4,
    },
    {
        team_id: 2,
        name: 'Market Risk Team',
        description: null,
        is_active: false,
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-04T00:00:00Z',
        lob_count: 1,
        model_count: 1,
    },
];

const sampleTeamDetail = {
    ...sampleTeams[0],
    lob_units: [],
};

const setupLayoutMocks = () => {
    mockGet.mockImplementation((url: string) => {
        switch (url) {
            case '/validation-workflow/my-pending-submissions':
                return Promise.resolve({ data: [] });
            case '/deployment-tasks/my-tasks':
                return Promise.resolve({ data: [] });
            case '/decommissioning/pending-validator-review':
                return Promise.resolve({ data: [] });
            case '/monitoring/my-tasks':
                return Promise.resolve({ data: [] });
            case '/attestations/my-upcoming':
                return Promise.resolve({ data: { pending_count: 0 } });
            case '/validation-workflow/my-pending-approvals':
                return Promise.resolve({ data: [] });
            case '/recommendations/my-tasks':
                return Promise.resolve({ data: { total_tasks: 0 } });
            case '/dashboard/mrsa-reviews/summary':
                return Promise.resolve({ data: { overdue_count: 0, no_irp_count: 0, never_reviewed_count: 0 } });
            default:
                return Promise.resolve({ data: [] });
        }
    });
};

describe('TeamsPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockGetTeams.mockReset();
        mockGetTeam.mockReset();
        mockCreateTeam.mockReset();
        mockUpdateTeam.mockReset();
        mockDeleteTeam.mockReset();
    });

    it('renders teams list', async () => {
        setupLayoutMocks();
        mockGetTeams.mockResolvedValue({ data: sampleTeams });

        render(<TeamsPage />);

        await waitFor(() => {
            expect(screen.getByText('Credit Risk Team')).toBeInTheDocument();
            expect(screen.getByText('Market Risk Team')).toBeInTheDocument();
        });
    });

    it('creates a new team', async () => {
        setupLayoutMocks();
        mockGetTeams.mockResolvedValue({ data: sampleTeams });
        mockCreateTeam.mockResolvedValue({ data: sampleTeams[0] });

        render(<TeamsPage />);

        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: '+ New Team' }));
        });

        fireEvent.change(screen.getByPlaceholderText('Team name'), {
            target: { value: 'New Team' },
        });

        fireEvent.click(screen.getByRole('button', { name: 'Create Team' }));

        await waitFor(() => {
            expect(mockCreateTeam).toHaveBeenCalledWith({
                name: 'New Team',
                description: null,
                is_active: true,
            });
        });
    });

    it('edits an existing team', async () => {
        setupLayoutMocks();
        mockGetTeams.mockResolvedValue({ data: sampleTeams });
        mockUpdateTeam.mockResolvedValue({ data: sampleTeams[0] });

        render(<TeamsPage />);

        await waitFor(() => {
            fireEvent.click(screen.getAllByText('Edit')[0]);
        });

        fireEvent.change(screen.getByPlaceholderText('Team name'), {
            target: { value: 'Credit Risk Updated' },
        });

        fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));

        await waitFor(() => {
            expect(mockUpdateTeam).toHaveBeenCalledWith(1, {
                name: 'Credit Risk Updated',
                description: 'Credit team',
                is_active: true,
            });
        });
    });

    it('loads team details when selecting a team', async () => {
        setupLayoutMocks();
        mockGetTeams.mockResolvedValue({ data: sampleTeams });
        mockGetTeam.mockResolvedValue({ data: sampleTeamDetail });

        render(<TeamsPage />);

        await waitFor(() => {
            fireEvent.click(screen.getAllByText('View')[0]);
        });

        await waitFor(() => {
            expect(mockGetTeam).toHaveBeenCalledWith(1);
            expect(screen.getByText('Select a team to view details and manage LOB assignments.')).not.toBeInTheDocument();
            expect(screen.getByText('Credit Risk Team')).toBeInTheDocument();
        });
    });
});

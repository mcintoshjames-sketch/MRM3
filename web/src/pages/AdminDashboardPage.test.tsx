import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import AdminDashboardPage from './AdminDashboardPage';

// Mock the API client
const mockGet = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

// Mock the AuthContext with Admin user
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

const sampleOverdueModels = [
    {
        model_id: 1,
        model_name: 'Credit Risk Model',
        risk_tier: 'Tier 1',
        owner_name: 'John Doe',
        last_validation_date: '2024-06-15',
        next_due_date: '2024-12-15',
        days_overdue: 45,
        status: 'Overdue',
    },
    {
        model_id: 2,
        model_name: 'Market Risk Model',
        risk_tier: 'Tier 2',
        owner_name: 'Jane Smith',
        last_validation_date: null,
        next_due_date: null,
        days_overdue: null,
        status: 'Never Validated',
    },
];

const samplePassWithFindings = [
    {
        validation_id: 1,
        model_id: 3,
        model_name: 'Fraud Detection Model',
        validation_date: '2025-01-10',
        validator_name: 'Validator User',
        findings_summary: 'Data quality issues found',
        has_recommendations: false,
    },
];

const setupApiMocks = (overdue = sampleOverdueModels, findings = samplePassWithFindings) => {
    mockGet.mockImplementation((url: string) => {
        if (url === '/validations/dashboard/overdue') {
            return Promise.resolve({ data: overdue });
        }
        if (url === '/validations/dashboard/pass-with-findings') {
            return Promise.resolve({ data: findings });
        }
        if (url === '/validation-workflow/dashboard/sla-violations') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/validation-workflow/dashboard/out-of-order') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/validation-workflow/dashboard/pending-assignments') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/validation-workflow/dashboard/overdue-submissions') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/validation-workflow/dashboard/overdue-validations') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/validation-workflow/dashboard/upcoming-revalidations?days_ahead=90') {
            return Promise.resolve({ data: [] });
        }
        return Promise.reject(new Error('Unknown URL: ' + url));
    });
};

describe('AdminDashboardPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('displays loading state initially', () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('displays welcome message with user name', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText(/Welcome back, Admin User/)).toBeInTheDocument();
        });
    });

    it('displays dashboard title', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
        });
    });

    it('displays overdue validations count', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('2')).toBeInTheDocument();
            expect(screen.getByText('Overdue Validations')).toBeInTheDocument();
        });
    });

    it('displays pass with findings count', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('1')).toBeInTheDocument();
            expect(screen.getByText('Pass with Findings')).toBeInTheDocument();
        });
    });

    it('displays quick action links', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText(/View All Validations/)).toBeInTheDocument();
            expect(screen.getByText(/Configure Validation Policy/)).toBeInTheDocument();
        });
    });

    it('displays overdue models table', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('Models Overdue for Validation (2)')).toBeInTheDocument();
            expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
            expect(screen.getByText('Market Risk Model')).toBeInTheDocument();
        });
    });

    it('displays risk tier badges', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('Tier 1')).toBeInTheDocument();
            expect(screen.getByText('Tier 2')).toBeInTheDocument();
        });
    });

    it('displays owner names in overdue table', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('John Doe')).toBeInTheDocument();
            expect(screen.getByText('Jane Smith')).toBeInTheDocument();
        });
    });

    it('displays overdue status with days', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText(/Overdue.*45 days/)).toBeInTheDocument();
            expect(screen.getByText('Never Validated')).toBeInTheDocument();
        });
    });

    it('displays create validation links', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            const createLinks = screen.getAllByText('Create Validation');
            expect(createLinks.length).toBe(2);
        });
    });

    it('displays pass with findings table', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('Validations with Findings (1)')).toBeInTheDocument();
            expect(screen.getByText('Fraud Detection Model')).toBeInTheDocument();
        });
    });

    it('displays validation date and validator name', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('2025-01-10')).toBeInTheDocument();
            expect(screen.getByText('Validator User')).toBeInTheDocument();
        });
    });

    it('displays findings summary', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('Data quality issues found')).toBeInTheDocument();
        });
    });

    it('displays no recommendations badge', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('No Recommendations')).toBeInTheDocument();
        });
    });

    it('displays empty state for no overdue models', async () => {
        setupApiMocks([], samplePassWithFindings);
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('No models are currently overdue for validation.')).toBeInTheDocument();
        });
    });

    it('displays empty state for no pass with findings', async () => {
        setupApiMocks(sampleOverdueModels, []);
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText('No validations with findings requiring attention.')).toBeInTheDocument();
        });
    });

    it('displays zero counts when no data', async () => {
        setupApiMocks([], []);
        render(<AdminDashboardPage />);
        await waitFor(() => {
            const zeroCounts = screen.getAllByText('0');
            expect(zeroCounts.length).toBe(2);
        });
    });
});

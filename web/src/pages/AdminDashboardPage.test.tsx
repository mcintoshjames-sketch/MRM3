import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '../test/utils';
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

const sampleSLAViolations = [
    {
        request_id: 10,
        model_name: 'Credit Risk Model',
        violation_type: 'Lead time exceeded',
        sla_days: 60,
        actual_days: 75,
        days_overdue: 15,
        current_status: 'IN_PROGRESS',
        priority: 'High',
        severity: 'high',
        timestamp: '2025-01-10T00:00:00Z',
    },
];

const sampleOutOfOrder = [
    {
        request_id: 20,
        model_name: 'Market Risk Model',
        version_number: '1.2',
        validation_type: 'INITIAL',
        target_completion_date: '2025-02-15T00:00:00Z',
        production_date: '2025-01-01T00:00:00Z',
        days_gap: 45,
        current_status: 'REVIEW',
        priority: 'Medium',
        severity: 'high',
        is_interim: false,
    },
];

const samplePendingAssignments = [
    {
        request_id: 30,
        model_id: 3,
        model_name: 'Fraud Detection Model',
        requestor_name: 'Alice Smith',
        validation_type: 'ANNUAL',
        priority: 'High',
        region: 'US',
        request_date: '2025-01-05T00:00:00Z',
        target_completion_date: '2025-03-01T00:00:00Z',
        days_pending: 10,
        severity: 'critical',
    },
];

const sampleOverdueSubmissions = [
    {
        request_id: 40,
        model_id: 4,
        model_name: 'Liquidity Model',
        model_owner: 'Bob Jones',
        submission_due_date: '2025-01-01',
        grace_period_end: '2025-01-31',
        days_overdue: 12,
        urgency: 'overdue',
        validation_due_date: '2025-02-28',
        submission_status: 'pending',
    },
];

const sampleOverdueValidations = [
    {
        request_id: 50,
        model_id: 5,
        model_name: 'Pricing Model',
        model_owner: 'Carol Miller',
        submission_received_date: '2025-01-10',
        model_validation_due_date: '2025-02-10',
        days_overdue: 5,
        current_status: 'PENDING_APPROVAL',
        model_compliance_status: 'overdue',
    },
];

const sampleUpcomingRevalidations = [
    {
        model_id: 6,
        model_name: 'Treasury Model',
        model_owner: 'Dana Lee',
        risk_tier: 'Tier 2',
        status: 'Upcoming',
        last_validation_date: '2024-06-15',
        next_submission_due: '2025-03-15',
        next_validation_due: '2025-06-15',
        days_until_submission_due: 60,
        days_until_validation_due: 150,
    },
];

const samplePendingModelSubmissions = [
    {
        model_id: 7,
        model_name: 'Collections Model',
        description: 'New model awaiting approval',
        development_type: 'New',
        owner: { full_name: 'Evan Green' },
        submitted_by_user: { full_name: 'Frank White' },
        submitted_at: '2025-02-01T00:00:00Z',
        row_approval_status: 'new',
    },
];

const sampleMrsaPastDue = [
    {
        mrsa_id: 101,
        mrsa_name: 'Credit Risk MRSA',
        risk_level: 'High-Risk',
        last_review_date: '2023-01-01',
        next_due_date: '2024-01-01',
        status: 'OVERDUE',
        days_until_due: -120,
        owner: { user_id: 2, full_name: 'Dana Lee', email: 'dana@example.com' },
        has_exception: false,
        exception_due_date: null,
    },
];

const setupApiMocks = (overrides: Partial<Record<string, any>> = {}) => {
    const data = {
        slaViolations: sampleSLAViolations,
        outOfOrder: sampleOutOfOrder,
        pendingAssignments: samplePendingAssignments,
        overdueSubmissions: sampleOverdueSubmissions,
        overdueValidations: sampleOverdueValidations,
        upcomingRevalidations: sampleUpcomingRevalidations,
        pendingModelSubmissions: samplePendingModelSubmissions,
        pendingModelEdits: [],
        pendingAdditionalApprovals: [],
        myOverdueItems: [],
        monitoringOverview: { cycles: [] },
        recommendationsOpen: { total_open: 0, overdue_count: 0, by_status: [], by_priority: [] },
        recommendationsOverdue: { recommendations: [] },
        mrsaPastDue: sampleMrsaPastDue,
        cycleReminder: { should_show_reminder: false },
        attestationStats: { submitted_count: 0 },
        ...overrides,
    };

    mockGet.mockImplementation((url: string) => {
        switch (url) {
            case '/validation-workflow/dashboard/sla-violations':
                return Promise.resolve({ data: data.slaViolations });
            case '/validation-workflow/dashboard/out-of-order':
                return Promise.resolve({ data: data.outOfOrder });
            case '/validation-workflow/dashboard/pending-assignments':
                return Promise.resolve({ data: data.pendingAssignments });
            case '/validation-workflow/dashboard/overdue-submissions':
                return Promise.resolve({ data: data.overdueSubmissions });
            case '/validation-workflow/dashboard/overdue-validations':
                return Promise.resolve({ data: data.overdueValidations });
            case '/validation-workflow/dashboard/upcoming-revalidations?days_ahead=90':
                return Promise.resolve({ data: data.upcomingRevalidations });
            case '/models/pending-submissions':
                return Promise.resolve({ data: data.pendingModelSubmissions });
            case '/models/pending-edits/all':
                return Promise.resolve({ data: data.pendingModelEdits });
            case '/validation-workflow/dashboard/pending-additional-approvals':
                return Promise.resolve({ data: data.pendingAdditionalApprovals });
            case '/validation-workflow/dashboard/my-overdue-items':
                return Promise.resolve({ data: data.myOverdueItems });
            case '/monitoring/admin-overview':
                return Promise.resolve({ data: data.monitoringOverview });
            case '/recommendations/dashboard/open':
                return Promise.resolve({ data: data.recommendationsOpen });
            case '/recommendations/dashboard/overdue':
                return Promise.resolve({ data: data.recommendationsOverdue });
            case '/dashboard/mrsa-reviews/overdue':
                return Promise.resolve({ data: data.mrsaPastDue });
            case '/attestations/cycles/reminder':
                return Promise.resolve({ data: data.cycleReminder });
            case '/attestations/dashboard/stats':
                return Promise.resolve({ data: data.attestationStats });
            case '/validation-workflow/my-pending-submissions':
                return Promise.resolve({ data: [] });
            case '/deployment-tasks/my-tasks':
                return Promise.resolve({ data: [] });
            default:
                return Promise.reject(new Error('Unknown URL: ' + url));
        }
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

    it('displays quick action links', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);
        await waitFor(() => {
            expect(screen.getByText(/View All Validations/)).toBeInTheDocument();
            expect(screen.getByText(/Configure Workflow SLA/)).toBeInTheDocument();
        });
    });

    it('renders dashboard metrics based on API data', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
        });

        expect(screen.getByText('Pending Assignment')).toBeInTheDocument();
        expect(screen.getByText('Lead Time Violations')).toBeInTheDocument();
        expect(screen.getByText('Out of Order')).toBeInTheDocument();
        expect(screen.getAllByText('Pending Submissions').length).toBeGreaterThan(0);
        expect(screen.getByText('Overdue Validations')).toBeInTheDocument();

        expect(screen.getByText('1 awaiting')).toBeInTheDocument();
        expect(screen.getAllByText('1 active').length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Pending Submissions/i).length).toBeGreaterThan(0);
    });

    it('displays pending validator assignments feed when data present', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('Pending Validator Assignments')).toBeInTheDocument();
        });

        expect(screen.getByText('Fraud Detection Model')).toBeInTheDocument();
        expect(screen.getByText('Assign Validator')).toBeInTheDocument();
    });

    it('shows overdue submissions table when data present', async () => {
        setupApiMocks();
        render(<AdminDashboardPage />);

        await waitFor(() => {
            expect(screen.getByText(/Pending and Overdue Revalidation Submissions/)).toBeInTheDocument();
        });

        const row = screen.getByText('Liquidity Model').closest('tr');
        expect(row).not.toBeNull();
        expect(within(row as HTMLElement).getByText('Overdue')).toBeInTheDocument();
    });

    it('hides data sections when API returns no rows but keeps summary cards', async () => {
        setupApiMocks({
            slaViolations: [],
            outOfOrder: [],
            pendingAssignments: [],
            overdueSubmissions: [],
            overdueValidations: [],
            upcomingRevalidations: [],
            pendingModelSubmissions: [],
            mrsaPastDue: [],
        });

        render(<AdminDashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
        });

        expect(screen.queryByText('Pending Validator Assignments')).not.toBeInTheDocument();
        expect(screen.queryByText(/Pending and Overdue Revalidation Submissions/)).not.toBeInTheDocument();
        expect(screen.getByText('Pending Assignment')).toBeInTheDocument();
        expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(5);
    });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import BulkAttestationPage from './BulkAttestationPage';
import { BulkAttestationStateResponse } from '../hooks/useBulkAttestation';

// Mock useParams to return cycleId
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useParams: () => ({ cycleId: '1' }),
        useNavigate: () => vi.fn(),
    };
});

// Mock the API client
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: unknown[]) => mockGet(...args),
        post: (...args: unknown[]) => mockPost(...args),
        delete: (...args: unknown[]) => mockDelete(...args),
    },
}));

// Mock the AuthContext
vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: {
            user_id: 1,
            email: 'owner@example.com',
            full_name: 'Model Owner',
            role: 'user',
        },
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
    }),
}));

// Sample test data
const sampleCycle = {
    cycle_id: 1,
    cycle_name: 'Q4 2024 Attestation',
    submission_due_date: '2024-12-31',
    status: 'ACTIVE',
    days_until_due: 30,
};

const sampleQuestions = [
    {
        value_id: 101,
        code: 'ATT_Q1',
        label: 'Model performs as expected',
        description: 'Confirm the model continues to perform within acceptable parameters',
        requires_comment_if_no: true,
        sort_order: 1,
    },
];

const samplePendingModels = [
    {
        attestation_id: 1,
        model_id: 10,
        model_name: 'Credit Risk Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15',
        attestation_status: 'PENDING' as const,
        is_excluded: false,
    },
    {
        attestation_id: 2,
        model_id: 20,
        model_name: 'Fraud Detection Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15',
        attestation_status: 'PENDING' as const,
        is_excluded: true,
    },
];

const sampleSubmittedModels = [
    {
        ...samplePendingModels[0],
        attestation_status: 'SUBMITTED' as const,
    },
    {
        ...samplePendingModels[1],
        attestation_status: 'SUBMITTED' as const,
        is_excluded: false,
    },
];

const sampleSummary = {
    total_models: 2,
    pending_count: 2,
    excluded_count: 1,
    submitted_count: 0,
    accepted_count: 0,
    rejected_count: 0,
};

const createMockResponse = (overrides: Partial<BulkAttestationStateResponse> = {}): BulkAttestationStateResponse => ({
    cycle: sampleCycle,
    models: samplePendingModels,
    questions: sampleQuestions,
    draft: {
        exists: false,
        bulk_submission_id: null,
        selected_model_ids: [],
        excluded_model_ids: [],
        responses: [],
        comment: null,
        last_saved: null,
    },
    summary: sampleSummary,
    ...overrides,
});

// Helper to setup mock for bulk attestation endpoint + Layout
const setupApiMocks = (bulkResponse: BulkAttestationStateResponse) => {
    mockGet.mockImplementation((url: string) => {
        if (url.startsWith('/attestations/bulk/')) {
            return Promise.resolve({ data: bulkResponse });
        }
        if (url === '/validation-workflow/my-pending-submissions') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/deployment-tasks/my-tasks') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/decommissioning/my-pending-approvals') {
            return Promise.resolve({ data: [] });
        }
        if (url === '/monitoring/my-tasks') {
            return Promise.resolve({ data: { tasks: [] } });
        }
        if (url.startsWith('/attestations/my')) {
            return Promise.resolve({ data: [] });
        }
        return Promise.resolve({ data: [] });
    });
};

describe('BulkAttestationPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockPost.mockReset();
        mockDelete.mockReset();
    });

    describe('loading state', () => {
        it('shows loading indicator initially', () => {
            mockGet.mockImplementation(() => new Promise(() => {})); // Never resolves

            render(<BulkAttestationPage />);

            expect(screen.getByText('Loading bulk attestation...')).toBeInTheDocument();
        });
    });

    describe('cycle not found', () => {
        it('shows error when cycle not found', async () => {
            mockGet.mockImplementation((url: string) => {
                if (url.startsWith('/attestations/bulk/')) {
                    return Promise.reject({
                        response: { data: { detail: 'Cycle not found' } },
                    });
                }
                return Promise.resolve({ data: [] });
            });

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('Cycle Not Found')).toBeInTheDocument();
            });
        });
    });

    describe('completion summary view (Finding 2)', () => {
        it('shows completion summary when all models are submitted', async () => {
            setupApiMocks(createMockResponse({
                models: sampleSubmittedModels,
                summary: {
                    ...sampleSummary,
                    pending_count: 0,
                    submitted_count: 2,
                },
            }));

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('Bulk Attestation Summary')).toBeInTheDocument();
                expect(screen.getByText('Bulk Attestation Complete')).toBeInTheDocument();
            });
        });

        it('shows "No Pending Models" when user has no models', async () => {
            setupApiMocks(createMockResponse({
                models: [],
                summary: {
                    total_models: 0,
                    pending_count: 0,
                    excluded_count: 0,
                    submitted_count: 0,
                    accepted_count: 0,
                    rejected_count: 0,
                },
            }));

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('No Pending Models')).toBeInTheDocument();
            });
        });
    });

    describe('main attestation form view', () => {
        it('renders cycle header with due date', async () => {
            setupApiMocks(createMockResponse());

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('Bulk Attestation')).toBeInTheDocument();
                expect(screen.getByText('Q4 2024 Attestation')).toBeInTheDocument();
            });
        });

        it('renders model selection section with models', async () => {
            setupApiMocks(createMockResponse());

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('Step 1: Select Models')).toBeInTheDocument();
                expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
            });
        });

        it('renders attestation questions', async () => {
            setupApiMocks(createMockResponse());

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText('Step 2: Answer Attestation Questions')).toBeInTheDocument();
                expect(screen.getByText('Model performs as expected')).toBeInTheDocument();
            });
        });
    });

    describe('excluded models (Finding 1)', () => {
        it('shows excluded models warning when models are excluded', async () => {
            setupApiMocks(createMockResponse());

            render(<BulkAttestationPage />);

            await waitFor(() => {
                expect(screen.getByText(/1 model excluded from bulk attestation/)).toBeInTheDocument();
            });
        });
    });

    describe('navigation', () => {
        it('renders back link to My Attestations', async () => {
            setupApiMocks(createMockResponse());

            render(<BulkAttestationPage />);

            await waitFor(() => {
                const backLink = screen.getByRole('link', { name: /Back to My Attestations/ });
                expect(backLink).toHaveAttribute('href', '/my-attestations');
            });
        });
    });
});

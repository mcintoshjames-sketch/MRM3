import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import ModelDetailsPage from './ModelDetailsPage';

// Mock the API client
const mockGet = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
        patch: (...args: any[]) => mockPatch(...args),
        delete: (...args: any[]) => mockDelete(...args),
    },
}));

// Mock useParams to return model ID
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useParams: () => ({ id: '1' }),
        useNavigate: () => vi.fn(),
    };
});

// Mock the AuthContext
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

const sampleModel = {
    model_id: 1,
    model_name: 'Credit Risk Model',
    description: 'Predicts credit risk for loan applications',
    development_type: 'In-House',
    owner_id: 1,
    developer_id: 2,
    vendor_id: null,
    risk_tier_id: 1,
    validation_type_id: null,
    model_type_id: null,
    status: 'Active',
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-15T14:30:00Z',
    owner: {
        user_id: 1,
        email: 'owner@example.com',
        full_name: 'Model Owner',
        role: 'User',
    },
    developer: {
        user_id: 2,
        email: 'dev@example.com',
        full_name: 'Model Developer',
        role: 'User',
    },
    vendor: null,
    risk_tier: {
        value_id: 1,
        taxonomy_id: 1,
        code: 'TIER_1',
        label: 'Tier 1',
        description: 'High risk',
        sort_order: 1,
        is_active: true,
    },
    validation_type: null,
    model_type: null,
    users: [
        { user_id: 3, email: 'user1@example.com', full_name: 'User One', role: 'User' },
        { user_id: 4, email: 'user2@example.com', full_name: 'User Two', role: 'User' },
    ],
    regulatory_categories: [],
};

const sampleUsers = [
    { user_id: 1, email: 'owner@example.com', full_name: 'Model Owner', role: 'User' },
    { user_id: 2, email: 'dev@example.com', full_name: 'Model Developer', role: 'User' },
    { user_id: 3, email: 'user1@example.com', full_name: 'User One', role: 'User' },
    { user_id: 4, email: 'user2@example.com', full_name: 'User Two', role: 'User' },
];

const sampleVendors = [
    { vendor_id: 1, name: 'Vendor Corp', contact_info: 'vendor@corp.com' },
];

const sampleTaxonomies = [
    { taxonomy_id: 1, name: 'Model Risk Tier', description: null, is_system: true, values: [] },
];

const sampleTaxonomyDetails = {
    taxonomy_id: 1,
    name: 'Model Risk Tier',
    description: null,
    is_system: true,
    values: [
        { value_id: 1, taxonomy_id: 1, code: 'TIER_1', label: 'Tier 1', description: 'High', sort_order: 1, is_active: true },
        { value_id: 2, taxonomy_id: 1, code: 'TIER_2', label: 'Tier 2', description: 'Medium', sort_order: 2, is_active: true },
    ],
};

const sampleValidations = [
    {
        validation_id: 1,
        model_id: 1,
        model_name: 'Credit Risk Model',
        validation_date: '2025-01-15',
        validator_name: 'Validator User',
        validation_type: 'Initial',
        outcome: 'Pass',
        scope: 'Full Scope',
        created_at: '2025-01-15T10:00:00Z',
    },
    {
        validation_id: 2,
        model_id: 1,
        model_name: 'Credit Risk Model',
        validation_date: '2025-01-10',
        validator_name: 'Admin User',
        validation_type: 'Annual Review',
        outcome: 'Pass with Findings',
        scope: 'Targeted Review',
        created_at: '2025-01-10T10:00:00Z',
    },
];

const setupApiMocks = (validations = sampleValidations, modelData = sampleModel) => {
    mockGet.mockImplementation((url: string) => {
        if (url === '/models/1') return Promise.resolve({ data: modelData });
        if (url === '/auth/users') return Promise.resolve({ data: sampleUsers });
        if (url === '/vendors/') return Promise.resolve({ data: sampleVendors });
        if (url === '/regions/') return Promise.resolve({ data: [] });
        if (url === '/taxonomies/') return Promise.resolve({ data: sampleTaxonomies });
        if (url === '/taxonomies/1') return Promise.resolve({ data: sampleTaxonomyDetails });
        if (url === '/validations/?model_id=1') return Promise.resolve({ data: validations });
        if (url === '/validation-workflow/requests/?model_id=1') return Promise.resolve({ data: [] });
        if (url === '/models/1/versions') return Promise.resolve({ data: [] });
        if (url === '/models/1/revalidation-status') return Promise.resolve({ data: { status: 'Never Validated' } });
        return Promise.reject(new Error(`Unknown URL: ${url}`));
    });
};

describe('ModelDetailsPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockPatch.mockReset();
        mockDelete.mockReset();
    });

    it('displays loading state initially', () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('displays model name after loading', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
        });
    });

    it('displays model details tab content', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Model ID')).toBeInTheDocument();
            expect(screen.getByText('1')).toBeInTheDocument();
            expect(screen.getByText('Active')).toBeInTheDocument();
            expect(screen.getByText('In-House')).toBeInTheDocument();
        });
    });

    it('displays owner and developer information', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Model Owner')).toBeInTheDocument();
            expect(screen.getByText('owner@example.com')).toBeInTheDocument();
            expect(screen.getByText('Model Developer')).toBeInTheDocument();
            expect(screen.getByText('dev@example.com')).toBeInTheDocument();
        });
    });

    it('displays model description', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Predicts credit risk for loan applications')).toBeInTheDocument();
        });
    });

    it('displays model users', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('User One')).toBeInTheDocument();
            expect(screen.getByText('User Two')).toBeInTheDocument();
        });
    });

    it('displays risk tier badge', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Tier 1')).toBeInTheDocument();
        });
    });

    it('displays back to models button', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText(/Back to Models/)).toBeInTheDocument();
        });
    });

    it('displays edit and delete buttons', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Edit Model')).toBeInTheDocument();
            expect(screen.getByText('Delete')).toBeInTheDocument();
        });
    });

    it('displays tabs for details and validation history', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Model Details')).toBeInTheDocument();
            expect(screen.getByText(/Validation History/)).toBeInTheDocument();
        });
    });

    it('shows validation count in tab', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Validation History (2)')).toBeInTheDocument();
        });
    });

    it('switches to validation history tab when clicked', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Validation History (2)')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Validation History (2)'));

        await waitFor(() => {
            // Check for validation history table headers
            expect(screen.getByText('Date')).toBeInTheDocument();
            expect(screen.getByText('Validator')).toBeInTheDocument();
            expect(screen.getByText('Type')).toBeInTheDocument();
            expect(screen.getByText('Outcome')).toBeInTheDocument();
            expect(screen.getByText('Scope')).toBeInTheDocument();
        });
    });

    it('displays validation records in history tab', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByText('Validation History (2)'));
        });

        await waitFor(() => {
            expect(screen.getByText('2025-01-15')).toBeInTheDocument();
            expect(screen.getByText('2025-01-10')).toBeInTheDocument();
            expect(screen.getByText('Validator User')).toBeInTheDocument();
            expect(screen.getByText('Initial')).toBeInTheDocument();
            expect(screen.getByText('Annual Review')).toBeInTheDocument();
            expect(screen.getByText('Pass')).toBeInTheDocument();
            expect(screen.getByText('Pass with Findings')).toBeInTheDocument();
        });
    });

    it('displays empty state when no validations', async () => {
        setupApiMocks([]);
        render(<ModelDetailsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByText('Validation History (0)'));
        });

        await waitFor(() => {
            expect(screen.getByText('No validation records found for this model.')).toBeInTheDocument();
        });
    });

    it('displays new validation button in history tab', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByText('Validation History (2)'));
        });

        await waitFor(() => {
            expect(screen.getByText('+ New Validation')).toBeInTheDocument();
        });
    });

    it('opens edit form when edit button clicked', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Edit Model')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Edit Model'));

        await waitFor(() => {
            expect(screen.getByText('Edit Model', { selector: 'h3' })).toBeInTheDocument();
            expect(screen.getByLabelText('Model Name')).toBeInTheDocument();
        });
    });

    it('closes edit form when cancel clicked', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByText('Edit Model'));
        });

        await waitFor(() => {
            expect(screen.getByText('Cancel')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Cancel'));

        await waitFor(() => {
            // Should be back to view mode
            expect(screen.getByText('Edit Model', { selector: 'button' })).toBeInTheDocument();
        });
    });

    it('displays model not found when model fetch fails', async () => {
        mockGet.mockImplementation((url: string) => {
            if (url === '/models/1') return Promise.reject(new Error('Not found'));
            if (url === '/auth/users') return Promise.resolve({ data: sampleUsers });
            if (url === '/vendors/') return Promise.resolve({ data: sampleVendors });
            if (url === '/taxonomies/') return Promise.resolve({ data: sampleTaxonomies });
            return Promise.reject(new Error(`Unknown URL: ${url}`));
        });

        render(<ModelDetailsPage />);

        await waitFor(() => {
            expect(screen.getByText('Model Not Found')).toBeInTheDocument();
        });
    });

    it('displays model data even when validations fetch fails', async () => {
        mockGet.mockImplementation((url: string) => {
            if (url === '/models/1') return Promise.resolve({ data: sampleModel });
            if (url === '/auth/users') return Promise.resolve({ data: sampleUsers });
            if (url === '/vendors/') return Promise.resolve({ data: sampleVendors });
            if (url === '/taxonomies/') return Promise.resolve({ data: sampleTaxonomies });
            if (url === '/taxonomies/1') return Promise.resolve({ data: sampleTaxonomyDetails });
            if (url === '/validations/?model_id=1') return Promise.reject(new Error('Validations API error'));
            return Promise.reject(new Error(`Unknown URL: ${url}`));
        });

        render(<ModelDetailsPage />);

        await waitFor(() => {
            // Model should still display despite validation API failure
            expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
            expect(screen.getByText('Model Owner')).toBeInTheDocument();
        });
    });

    it('shows empty validation history when validations fetch fails', async () => {
        mockGet.mockImplementation((url: string) => {
            if (url === '/models/1') return Promise.resolve({ data: sampleModel });
            if (url === '/auth/users') return Promise.resolve({ data: sampleUsers });
            if (url === '/vendors/') return Promise.resolve({ data: sampleVendors });
            if (url === '/taxonomies/') return Promise.resolve({ data: sampleTaxonomies });
            if (url === '/taxonomies/1') return Promise.resolve({ data: sampleTaxonomyDetails });
            if (url === '/validations/?model_id=1') return Promise.reject(new Error('Validations API error'));
            return Promise.reject(new Error(`Unknown URL: ${url}`));
        });

        render(<ModelDetailsPage />);

        await waitFor(() => {
            // Should show 0 validations since fetch failed
            expect(screen.getByText('Validation History (0)')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Validation History (0)'));

        await waitFor(() => {
            expect(screen.getByText('No validation records found for this model.')).toBeInTheDocument();
        });
    });

    it('displays third-party model with vendor', async () => {
        const thirdPartyModel = {
            ...sampleModel,
            development_type: 'Third-Party',
            vendor_id: 1,
            vendor: {
                vendor_id: 1,
                name: 'Vendor Corp',
                contact_info: 'vendor@corp.com',
            },
        };
        setupApiMocks(sampleValidations, thirdPartyModel);

        render(<ModelDetailsPage />);

        await waitFor(() => {
            expect(screen.getByText('Third-Party')).toBeInTheDocument();
            expect(screen.getByText('Vendor Corp')).toBeInTheDocument();
        });
    });

    it('displays no users message when model has no users', async () => {
        const modelNoUsers = {
            ...sampleModel,
            users: [],
        };
        setupApiMocks(sampleValidations, modelNoUsers);

        render(<ModelDetailsPage />);

        await waitFor(() => {
            expect(screen.getByText('No users assigned')).toBeInTheDocument();
        });
    });

    it('displays timestamps for model', async () => {
        setupApiMocks();
        render(<ModelDetailsPage />);
        await waitFor(() => {
            expect(screen.getByText('Created')).toBeInTheDocument();
            expect(screen.getByText('Last Updated')).toBeInTheDocument();
        });
    });
});

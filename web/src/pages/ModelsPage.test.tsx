import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import ModelsPage from './ModelsPage';

// Mock the API client
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
        post: (...args: any[]) => mockPost(...args),
        delete: (...args: any[]) => mockDelete(...args),
    },
}));

// Mock the AuthContext
const mockLogout = vi.fn();
vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: {
            user_id: 1,
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'user',
        },
        login: vi.fn(),
        logout: mockLogout,
        loading: false,
    }),
}));

// Mock window.confirm
const mockConfirm = vi.fn();
window.confirm = mockConfirm;
const mockAlert = vi.fn();
window.alert = mockAlert;

const sampleUsers = [
    { user_id: 1, email: 'test@example.com', full_name: 'Test User', role: 'user' },
    { user_id: 2, email: 'dev@example.com', full_name: 'Developer', role: 'user' },
];

const sampleVendors = [
    { vendor_id: 1, name: 'Bloomberg', contact_info: 'support@bloomberg.com' },
    { vendor_id: 2, name: 'MSCI', contact_info: 'support@msci.com' },
];

const sampleTeams = [
    { team_id: 1, name: 'Credit Risk Team', is_active: true, lob_count: 2, model_count: 5 },
    { team_id: 2, name: 'Market Risk Team', is_active: true, lob_count: 1, model_count: 3 },
];

const sampleTaxonomies = [
    {
        name: 'Model Usage Frequency',
        values: [{ value_id: 1, label: 'Daily', is_active: true, sort_order: 1 }],
    },
    { name: 'Validation Type', values: [] },
    { name: 'Validation Priority', values: [] },
    {
        name: 'MRSA Risk Level',
        values: [{ value_id: 99, label: 'High-Risk', code: 'HIGH_RISK', requires_irp: true, is_active: true, sort_order: 1 }],
    },
    {
        name: 'Model Risk Tier',
        values: [{ value_id: 10, label: 'Tier 1', is_active: true, sort_order: 1 }],
    },
    {
        name: 'Regulatory Category',
        values: [{ value_id: 20, label: 'Regulatory A', is_active: true, sort_order: 1 }],
    },
];

const sampleModels = [
    {
        model_id: 1,
        model_name: 'Test Model',
        description: 'A test model',
        development_type: 'In-House',
        owner_id: 1,
        developer_id: 2,
        vendor_id: null,
        status: 'Active',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner: sampleUsers[0],
        developer: sampleUsers[1],
        vendor: null,
        users: [sampleUsers[0]],
    },
    {
        model_id: 2,
        model_name: 'Third-Party Model',
        description: 'Vendor model',
        development_type: 'Third-Party',
        owner_id: 1,
        developer_id: null,
        vendor_id: 1,
        status: 'In Development',
        created_at: '2024-01-02T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        owner: sampleUsers[0],
        developer: null,
        vendor: sampleVendors[0],
        users: [],
    },
];

const sampleMapApplications = [
    {
        application_id: 101,
        application_code: 'APP-101',
        application_name: 'Risk Analytics Platform',
        owner_name: 'Jane Doe',
        department: 'Risk',
        criticality_tier: 'High',
        status: 'Active',
    },
    {
        application_id: 202,
        application_code: 'APP-202',
        application_name: 'Legacy Decommissioned Tool',
        owner_name: 'Legacy Owner',
        department: 'Finance',
        criticality_tier: 'Low',
        status: 'Decommissioned',
    },
];

// Helper to setup standard API mocks
const setupApiMocks = (models = sampleModels) => {
    mockGet.mockImplementation((url: string, config?: { params?: Record<string, any> }) => {
        if (url.startsWith('/models/')) return Promise.resolve({ data: models });
        if (url === '/auth/users') return Promise.resolve({ data: sampleUsers });
        if (url === '/vendors/') return Promise.resolve({ data: sampleVendors });
        if (url === '/regions/') return Promise.resolve({ data: [] });
        if (url === '/teams/') return Promise.resolve({ data: sampleTeams });
        if (url.startsWith('/taxonomies/by-names/')) return Promise.resolve({ data: sampleTaxonomies });
        if (url === '/model-types/categories') return Promise.resolve({ data: [] });
        if (url === '/methodology-library/categories') return Promise.resolve({ data: [] });
        if (url === '/export-views/?entity_type=models') return Promise.resolve({ data: [] });
        if (url === '/validation-workflow/my-pending-submissions') return Promise.resolve({ data: [] });
        if (url === '/deployment-tasks/my-tasks') return Promise.resolve({ data: [] });
        if (url === '/irps/mrsa-review-status') return Promise.resolve({ data: [] });
        if (url === '/map/applications') {
            const params = config?.params || {};
            const query = (params.search || '').toString().toLowerCase();
            const statusFilter = params.status;
            const filtered = sampleMapApplications.filter((application) => {
                const matchesSearch = !query
                    || application.application_name.toLowerCase().includes(query)
                    || application.application_code.toLowerCase().includes(query);
                const matchesStatus = !statusFilter || application.status === statusFilter;
                return matchesSearch && matchesStatus;
            });
            return Promise.resolve({ data: filtered });
        }
        return Promise.reject(new Error('Unknown URL: ' + url));
    });
};

const openCreateForm = async () => {
    fireEvent.click(screen.getByRole('button', { name: /Add Model/i }));
    await screen.findByLabelText('Model Name');
};

const fillRequiredCreateFields = async (modelName: string) => {
    fireEvent.change(screen.getByLabelText('Model Name'), {
        target: { value: modelName }
    });
    fireEvent.change(screen.getByLabelText(/Description and Purpose/), {
        target: { value: `${modelName} description` }
    });
    fireEvent.change(screen.getByLabelText('Owner (Required)'), {
        target: { value: 'Test User' }
    });
    fireEvent.click(await screen.findByText('test@example.com'));
    fireEvent.change(screen.getByLabelText('Developer (Required for In-House)'), {
        target: { value: 'Developer' }
    });
    fireEvent.click(await screen.findByText('dev@example.com'));
    fireEvent.change(screen.getByLabelText(/Typical Usage Frequency/), {
        target: { value: '1' }
    });
    fireEvent.change(screen.getByLabelText('Implementation Date (Required)'), {
        target: { value: '2024-01-01' }
    });
};

describe('ModelsPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockPost.mockReset();
        mockDelete.mockReset();
        mockLogout.mockReset();
        mockConfirm.mockReset();
        mockAlert.mockReset();
    });

    it('displays loading state initially', () => {
        mockGet.mockImplementation(() => new Promise(() => { })); // Never resolves
        render(<ModelsPage />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders navigation with user info', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            // User info is now split across elements in the Layout sidebar
            expect(screen.getByText('Test User')).toBeInTheDocument();
            expect(screen.getByText('(user)')).toBeInTheDocument();
        });
    });

    it('displays models table after loading', async () => {
        setupApiMocks();
        render(<ModelsPage />);
        await waitFor(() => {
            expect(screen.getByText('Test Model')).toBeInTheDocument();
            expect(screen.getByText('Third-Party Model')).toBeInTheDocument();
        });
    });

    it('shows model details in table', async () => {
        setupApiMocks();
        render(<ModelsPage />);
        await waitFor(() => {
            expect(screen.getByText('A test model')).toBeInTheDocument();
            expect(screen.getByText('In-House')).toBeInTheDocument();
            expect(screen.getByText('Third-Party')).toBeInTheDocument();
            expect(screen.getByText('Bloomberg')).toBeInTheDocument();
        });
    });

    it('displays empty state when no models', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            expect(screen.getByText(/No models yet/)).toBeInTheDocument();
        });
    });

    it('shows Add Model button', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Add Model/i })).toBeInTheDocument();
        });
    });

    it('opens create form when Add Model clicked', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: /Add Model/i }));
        });
        expect(screen.getByLabelText('Model Name')).toBeInTheDocument();
        expect(screen.getByLabelText('Development Type')).toBeInTheDocument();
        expect(screen.getByLabelText('Owner (Required)')).toBeInTheDocument();
        expect(screen.getByLabelText('Developer (Required for In-House)')).toBeInTheDocument();
    });

    it('closes form when Cancel clicked', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: /Add Model/i }));
        });
        fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(screen.queryByLabelText('Model Name')).not.toBeInTheDocument();
    });

    it('creates new model when form submitted', async () => {
        setupApiMocks();
        mockPost.mockResolvedValueOnce({ data: { model_id: 3, model_name: 'New Model' } });
        render(<ModelsPage />);

        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: /Add Model/i }));
        });

        fireEvent.change(screen.getByLabelText('Model Name'), {
            target: { value: 'New Model' }
        });
        fireEvent.change(screen.getByLabelText(/Description and Purpose/), {
            target: { value: 'New model description' }
        });
        fireEvent.change(screen.getByLabelText('Owner (Required)'), {
            target: { value: 'Test User' }
        });
        fireEvent.click(screen.getByText('test@example.com'));
        fireEvent.change(screen.getByLabelText('Developer (Required for In-House)'), {
            target: { value: 'Developer' }
        });
        fireEvent.click(screen.getByText('dev@example.com'));
        fireEvent.change(screen.getByLabelText(/Typical Usage Frequency/), {
            target: { value: '1' }
        });
        fireEvent.change(screen.getByLabelText('Implementation Date (Required)'), {
            target: { value: '2024-01-01' }
        });
        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledWith('/models/', expect.objectContaining({
                model_name: 'New Model',
                description: 'New model description',
                owner_id: 1,
                developer_id: 2,
                development_type: 'In-House',
                usage_frequency_id: 1,
                initial_implementation_date: '2024-01-01',
            }));
        });
    });

    it('shows vendor field when Third-Party selected', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);

        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: /Add Model/i }));
        });

        // Initially no vendor field
        expect(screen.queryByLabelText(/Vendor/)).not.toBeInTheDocument();

        // Select Third-Party
        fireEvent.change(screen.getByLabelText('Development Type'), {
            target: { value: 'Third-Party' }
        });

        // Now vendor field should appear
        expect(screen.getByLabelText(/Vendor/)).toBeInTheDocument();
    });

    it('blocks MRSA create when supporting application is not selected', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await openCreateForm();
        await fillRequiredCreateFields('MRSA Missing App');

        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Required rationale' } });

        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        expect(mockPost).not.toHaveBeenCalled();
        expect(mockAlert).toHaveBeenCalledWith('Please select a Related Application.');
    });

    it('includes supporting_application_id when MRSA supporting app is selected', async () => {
        setupApiMocks([]);
        mockPost.mockResolvedValueOnce({ data: { model_id: 88, model_name: 'MRSA With App' } });
        render(<ModelsPage />);
        await openCreateForm();
        await fillRequiredCreateFields('MRSA With App');

        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Required rationale' } });
        fireEvent.change(screen.getByLabelText(/Related Application/), { target: { value: 'Risk' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));
        fireEvent.click(await screen.findByText('Risk Analytics Platform'));

        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledWith('/models/', expect.objectContaining({
                is_mrsa: true,
                supporting_application_id: 101,
            }));
        });
    });

    it('clears selected supporting app when MRSA checkbox is unchecked', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await openCreateForm();
        await fillRequiredCreateFields('MRSA Clear On Uncheck');

        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Required rationale' } });
        fireEvent.change(screen.getByLabelText(/Related Application/), { target: { value: 'Risk' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));
        fireEvent.click(await screen.findByText('Risk Analytics Platform'));

        fireEvent.click(screen.getByLabelText(/Mark as MRSA/)); // uncheck
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/)); // re-check
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Rationale after re-check' } });
        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        expect(mockPost).not.toHaveBeenCalled();
        expect(mockAlert).toHaveBeenCalledWith('Please select a Related Application.');
    });

    it('clears MRSA supporting app when classification is switched back to Model', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await openCreateForm();
        await fillRequiredCreateFields('MRSA Clear On Classification Switch');

        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Required rationale' } });
        fireEvent.change(screen.getByLabelText(/Related Application/), { target: { value: 'Risk' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));
        fireEvent.click(await screen.findByText('Risk Analytics Platform'));

        fireEvent.click(screen.getByLabelText('Model'));
        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/MRSA Risk Level/), { target: { value: '99' } });
        fireEvent.change(screen.getByLabelText(/Risk Rationale/), { target: { value: 'Rationale after switching back' } });
        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        expect(mockPost).not.toHaveBeenCalled();
        expect(mockAlert).toHaveBeenCalledWith('Please select a Related Application.');
    });

    it('searches MAP applications with status Active filter', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await openCreateForm();
        await fillRequiredCreateFields('MRSA Search Filter');

        fireEvent.click(screen.getByLabelText('Non-Model'));
        fireEvent.click(screen.getByLabelText(/Mark as MRSA/));
        fireEvent.change(screen.getByLabelText(/Related Application/), { target: { value: 'Risk' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(mockGet).toHaveBeenCalledWith('/map/applications', expect.objectContaining({
                params: expect.objectContaining({
                    search: 'Risk',
                    status: 'Active',
                    limit: 20,
                })
            }));
        });
    });

    it('shows delete button for each model', async () => {
        setupApiMocks();
        render(<ModelsPage />);
        await waitFor(() => {
            const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
            expect(deleteButtons).toHaveLength(2);
        });
    });

    it('calls confirm before deleting', async () => {
        setupApiMocks();
        mockConfirm.mockReturnValueOnce(true);
        mockDelete.mockResolvedValueOnce({});
        render(<ModelsPage />);

        await waitFor(() => {
            const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
            fireEvent.click(deleteButtons[0]);
        });

        expect(mockConfirm).toHaveBeenCalledWith('Are you sure you want to delete this model?');
        await waitFor(() => {
            expect(mockDelete).toHaveBeenCalledWith('/models/1');
        });
    });

    it('does not delete when confirm cancelled', async () => {
        setupApiMocks();
        mockConfirm.mockReturnValueOnce(false);
        render(<ModelsPage />);

        await waitFor(() => {
            const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
            fireEvent.click(deleteButtons[0]);
        });

        expect(mockDelete).not.toHaveBeenCalled();
    });

    it('displays table headers correctly', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            // Wait for loading to complete first
            expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        });
        // Then check headers exist
        expect(screen.getByText('Name')).toBeInTheDocument();
        expect(screen.getByText('Type')).toBeInTheDocument();
        // "Owner" appears in sidebar nav and table header
        expect(screen.getAllByText('Owner').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('Developer')).toBeInTheDocument();
        // "Vendor" appears in filter label and table header
        expect(screen.getAllByText('Vendor').length).toBeGreaterThanOrEqual(1);
        // "Users" appears in sidebar nav and table header
        expect(screen.getAllByText('Users').length).toBeGreaterThanOrEqual(2);
        // "Status" appears in filter label and table header
        expect(screen.getAllByText('Status').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('calls logout when logout button clicked', async () => {
        setupApiMocks([]);
        render(<ModelsPage />);
        await waitFor(() => {
            fireEvent.click(screen.getByRole('button', { name: 'Logout' }));
        });
        expect(mockLogout).toHaveBeenCalled();
    });

    it('displays owner and developer names in table', async () => {
        setupApiMocks();
        render(<ModelsPage />);
        await waitFor(() => {
            // Check owner column shows full names (appears multiple times - nav + table)
            const testUserCells = screen.getAllByText('Test User');
            expect(testUserCells.length).toBeGreaterThan(0);
            // Check developer column (appears in header + data cell)
            const developerCells = screen.getAllByText('Developer');
            expect(developerCells.length).toBeGreaterThanOrEqual(2); // header + data
        });
    });
});

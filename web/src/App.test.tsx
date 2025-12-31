import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Mock all page components to isolate routing logic
vi.mock('./pages/LoginPage', () => ({
    default: () => <div data-testid="login-page">Login Page</div>
}));

vi.mock('./pages/ModelsPage', () => ({
    default: () => <div data-testid="models-page">Models Page</div>
}));

vi.mock('./pages/ModelDetailsPage', () => ({
    default: () => <div data-testid="model-details-page">Model Details Page</div>
}));

vi.mock('./pages/ValidationWorkflowPage', () => ({
    default: () => <div data-testid="validation-workflow-page">Validation Workflow Page</div>
}));

vi.mock('./pages/VendorsPage', () => ({
    default: () => <div data-testid="vendors-page">Vendors Page</div>
}));

vi.mock('./pages/VendorDetailsPage', () => ({
    default: () => <div data-testid="vendor-details-page">Vendor Details Page</div>
}));

vi.mock('./pages/UsersPage', () => ({
    default: () => <div data-testid="users-page">Users Page</div>
}));

vi.mock('./pages/UserDetailsPage', () => ({
    default: () => <div data-testid="user-details-page">User Details Page</div>
}));

vi.mock('./pages/TaxonomyPage', () => ({
    default: () => <div data-testid="taxonomy-page">Taxonomy Page</div>
}));

vi.mock('./pages/AuditPage', () => ({
    default: () => <div data-testid="audit-page">Audit Page</div>
}));

vi.mock('./pages/AdminDashboardPage', () => ({
    default: () => <div data-testid="admin-dashboard-page">Admin Dashboard Page</div>
}));

vi.mock('./pages/ModelOwnerDashboardPage', () => ({
    default: () => <div data-testid="model-owner-dashboard-page">Model Owner Dashboard Page</div>
}));

vi.mock('./pages/ValidatorDashboardPage', () => ({
    default: () => <div data-testid="validator-dashboard-page">Validator Dashboard Page</div>
}));

// Mock useAuth hook
const mockUseAuth = vi.fn();
vi.mock('./contexts/AuthContext', () => ({
    useAuth: () => mockUseAuth()
}));

const renderWithRouter = (initialRoute: string = '/') => {
    return render(
        <MemoryRouter initialEntries={[initialRoute]}>
            <App />
        </MemoryRouter>
    );
};

describe('App Routing - Unauthenticated', () => {
    beforeEach(() => {
        mockUseAuth.mockReturnValue({
            user: null,
            loading: false
        });
    });

    it('redirects to login when accessing protected route', () => {
        renderWithRouter('/models');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('shows login page at /login', () => {
        renderWithRouter('/login');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects root to login when not authenticated', () => {
        renderWithRouter('/');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects /validation-workflow to login', () => {
        renderWithRouter('/validation-workflow');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects /validation-workflow/new to login', () => {
        renderWithRouter('/validation-workflow/new');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects /dashboard to login', () => {
        renderWithRouter('/dashboard');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });
});

describe('App Routing - Authenticated User', () => {
    beforeEach(() => {
        mockUseAuth.mockReturnValue({
            user: {
                user_id: 1,
                email: 'user@example.com',
                full_name: 'Test User',
                role: 'User',
                capabilities: {
                    can_view_admin_dashboard: false,
                    can_view_validator_dashboard: false,
                    can_view_approver_dashboard: false,
                    can_view_audit_logs: false
                }
            },
            loading: false
        });
    });

    it('renders models page at /models', () => {
        renderWithRouter('/models');
        expect(screen.getByTestId('models-page')).toBeInTheDocument();
    });

    it('renders model details page at /models/:id', () => {
        renderWithRouter('/models/123');
        expect(screen.getByTestId('model-details-page')).toBeInTheDocument();
    });

    it('renders validation workflow page at /validation-workflow', () => {
        renderWithRouter('/validation-workflow');
        expect(screen.getByTestId('validation-workflow-page')).toBeInTheDocument();
    });

    it('renders validation workflow page at /validation-workflow/new', () => {
        renderWithRouter('/validation-workflow/new');
        expect(screen.getByTestId('validation-workflow-page')).toBeInTheDocument();
    });

    it('renders validation workflow page with query params at /validation-workflow/new?model_id=1', () => {
        renderWithRouter('/validation-workflow/new?model_id=1');
        expect(screen.getByTestId('validation-workflow-page')).toBeInTheDocument();
    });

    it('renders vendors page at /vendors', () => {
        renderWithRouter('/vendors');
        expect(screen.getByTestId('vendors-page')).toBeInTheDocument();
    });

    it('renders vendor details page at /vendors/:id', () => {
        renderWithRouter('/vendors/456');
        expect(screen.getByTestId('vendor-details-page')).toBeInTheDocument();
    });

    it('renders users page at /users', () => {
        renderWithRouter('/users');
        expect(screen.getByTestId('users-page')).toBeInTheDocument();
    });

    it('renders user details page at /users/:id', () => {
        renderWithRouter('/users/789');
        expect(screen.getByTestId('user-details-page')).toBeInTheDocument();
    });

    it('renders taxonomy page at /taxonomy', () => {
        renderWithRouter('/taxonomy');
        expect(screen.getByTestId('taxonomy-page')).toBeInTheDocument();
    });

    it('redirects regular user from /audit to /models', () => {
        renderWithRouter('/audit');
        expect(screen.getByTestId('models-page')).toBeInTheDocument();
    });

    it('redirects regular user from /dashboard to /models', () => {
        renderWithRouter('/dashboard');
        expect(screen.getByTestId('models-page')).toBeInTheDocument();
    });

    it('redirects root to /my-dashboard for regular user', async () => {
        renderWithRouter('/');
        expect(await screen.findByTestId('model-owner-dashboard-page')).toBeInTheDocument();
    });

    it('redirects /login to /my-dashboard when already authenticated as regular user', async () => {
        renderWithRouter('/login');
        expect(await screen.findByTestId('model-owner-dashboard-page')).toBeInTheDocument();
    });
});

describe('App Routing - Admin User', () => {
    beforeEach(() => {
        mockUseAuth.mockReturnValue({
            user: {
                user_id: 1,
                email: 'admin@example.com',
                full_name: 'Admin User',
                role: 'Admin',
                capabilities: {
                    can_view_admin_dashboard: true,
                    can_view_validator_dashboard: false,
                    can_view_approver_dashboard: true,
                    can_view_audit_logs: true
                }
            },
            loading: false
        });
    });

    it('renders admin dashboard at /dashboard', () => {
        renderWithRouter('/dashboard');
        expect(screen.getByTestId('admin-dashboard-page')).toBeInTheDocument();
    });

    it('redirects root to /dashboard for admin user', () => {
        renderWithRouter('/');
        expect(screen.getByTestId('admin-dashboard-page')).toBeInTheDocument();
    });

    it('redirects /login to /dashboard when already authenticated as admin', () => {
        renderWithRouter('/login');
        expect(screen.getByTestId('admin-dashboard-page')).toBeInTheDocument();
    });

    it('can access all user routes', () => {
        renderWithRouter('/models');
        expect(screen.getByTestId('models-page')).toBeInTheDocument();
    });

    it('renders audit page at /audit', () => {
        renderWithRouter('/audit');
        expect(screen.getByTestId('audit-page')).toBeInTheDocument();
    });
});

describe('App Routing - Loading State', () => {
    it('shows loading indicator when auth is loading', () => {
        mockUseAuth.mockReturnValue({
            user: null,
            loading: true
        });
        renderWithRouter('/');
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
});

describe('App Routing - Route Coverage', () => {
    beforeEach(() => {
        mockUseAuth.mockReturnValue({
            user: {
                user_id: 1,
                email: 'user@example.com',
                full_name: 'Test User',
                role: 'User',
                capabilities: {
                    can_view_admin_dashboard: false,
                    can_view_validator_dashboard: false,
                    can_view_approver_dashboard: false,
                    can_view_audit_logs: false
                }
            },
            loading: false
        });
    });

    // This test documents all routes that should exist
    const expectedRoutes = [
        { path: '/login', testId: 'login-page', requiresAuth: false },
        { path: '/dashboard', testId: 'admin-dashboard-page', requiresAdmin: true },
        { path: '/models', testId: 'models-page', requiresAuth: true },
        { path: '/models/1', testId: 'model-details-page', requiresAuth: true },
        { path: '/validation-workflow', testId: 'validation-workflow-page', requiresAuth: true },
        { path: '/validation-workflow/new', testId: 'validation-workflow-page', requiresAuth: true },
        { path: '/vendors', testId: 'vendors-page', requiresAuth: true },
        { path: '/vendors/1', testId: 'vendor-details-page', requiresAuth: true },
        { path: '/users', testId: 'users-page', requiresAuth: true },
        { path: '/users/1', testId: 'user-details-page', requiresAuth: true },
        { path: '/taxonomy', testId: 'taxonomy-page', requiresAuth: true },
        { path: '/audit', testId: 'audit-page', requiresAuth: true, requiresAuditAccess: true },
    ];

    it.each(
        expectedRoutes
            .filter(r => r.requiresAuth && !r.requiresAdmin && !r.requiresAuditAccess)
            .map(r => [r.path, r.testId])
    )('route %s renders %s', (path, testId) => {
        renderWithRouter(path);
        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });
});

describe('App Routing - Link Targets Validation', () => {
    // These tests ensure that common navigation targets have corresponding routes
    // This catches issues like the /validation-workflow/new missing route

    const commonLinkTargets = [
        '/models',
        '/models/1',
        '/validation-workflow',
        '/validation-workflow/new',
        '/vendors',
        '/vendors/1',
        '/users',
        '/users/1',
        '/taxonomy',
        '/audit',
        '/dashboard',
        '/login',
    ];

    beforeEach(() => {
        mockUseAuth.mockReturnValue({
            user: {
                user_id: 1,
                email: 'admin@example.com',
                full_name: 'Admin User',
                role: 'Admin',
                capabilities: {
                    can_view_admin_dashboard: true,
                    can_view_validator_dashboard: false,
                    can_view_approver_dashboard: true,
                    can_view_audit_logs: true
                }
            },
            loading: false
        });
    });

    it.each(commonLinkTargets)('route %s is accessible', (path) => {
        const { container } = renderWithRouter(path);
        // Should not show blank page (no content)
        expect(container.textContent).not.toBe('');
    });
});

import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import ModelOwnerDashboardPage from './ModelOwnerDashboardPage';

const mockGet = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: {
            user_id: 7,
            email: 'owner@example.com',
            full_name: 'Model Owner',
            role: 'User',
        },
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
    }),
}));

vi.mock('../components/Layout', () => ({
    default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

const sampleMrsaStatuses = [
    {
        mrsa_id: 101,
        mrsa_name: 'MRSA Demo: Overdue - Collateral Optimizer',
        risk_level: 'High-Risk',
        last_review_date: '2023-01-01',
        next_due_date: '2024-01-01',
        status: 'OVERDUE',
        days_until_due: -45,
        owner: { user_id: 7, full_name: 'Model Owner', email: 'owner@example.com' },
        has_exception: false,
        exception_due_date: null,
    },
];

const setupApiMocks = () => {
    mockGet.mockImplementation((url: string) => {
        if (url === '/dashboard/news-feed') return Promise.resolve({ data: [] });
        if (url === '/models/my-submissions') return Promise.resolve({ data: [] });
        if (url.startsWith('/validation-workflow/dashboard/recent-approvals')) return Promise.resolve({ data: [] });
        if (url === '/validation-workflow/my-overdue-items') return Promise.resolve({ data: [] });
        if (url === '/decommissioning/my-pending-owner-reviews') return Promise.resolve({ data: [] });
        if (url === '/attestations/my-upcoming') {
            return Promise.resolve({
                data: { pending_count: 0, overdue_count: 0, days_until_due: null, current_cycle: null },
            });
        }
        if (url === '/recommendations/my-tasks') {
            return Promise.resolve({ data: { total_tasks: 0, overdue_count: 0, tasks: [] } });
        }
        if (url === '/validation-workflow/dashboard/my-pending-approvals') {
            return Promise.resolve({ data: { count: 0, pending_approvals: [] } });
        }
        if (url === '/irps/mrsa-review-status') return Promise.resolve({ data: sampleMrsaStatuses });
        return Promise.reject(new Error('Unknown URL: ' + url));
    });
};

describe('ModelOwnerDashboardPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('shows the MRSA review attention alert and removes the dashboard widget', async () => {
        setupApiMocks();

        render(<ModelOwnerDashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('My Dashboard')).toBeInTheDocument();
        });

        expect(screen.getByText('MRSA Reviews Need Attention')).toBeInTheDocument();
        expect(screen.getByText('MRSA Demo: Overdue - Collateral Optimizer')).toBeInTheDocument();
        expect(screen.getByText('Overdue')).toBeInTheDocument();

        const viewAllLink = screen.getByRole('link', { name: 'View All' });
        expect(viewAllLink).toHaveAttribute('href', '/my-mrsa-reviews');

        expect(screen.queryByText('MRSA Review Status')).not.toBeInTheDocument();
    });
});

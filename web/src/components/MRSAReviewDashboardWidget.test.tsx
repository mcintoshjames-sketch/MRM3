import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '../test/utils';
import MRSAReviewDashboardWidget from './MRSAReviewDashboardWidget';

const mockGet = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

const sampleStatuses = [
    {
        mrsa_id: 1,
        mrsa_name: 'Alpha MRSA',
        risk_level: 'High-Risk',
        last_review_date: '2025-01-01',
        next_due_date: '2027-01-01',
        status: 'CURRENT',
        days_until_due: 700,
        owner: { user_id: 1, full_name: 'Alice Owner', email: 'alice@example.com' },
        has_exception: false,
        exception_due_date: null
    },
    {
        mrsa_id: 2,
        mrsa_name: 'Beta MRSA',
        risk_level: 'High-Risk',
        last_review_date: '2023-01-01',
        next_due_date: '2024-01-01',
        status: 'OVERDUE',
        days_until_due: -400,
        owner: { user_id: 2, full_name: 'Bob Owner', email: 'bob@example.com' },
        has_exception: false,
        exception_due_date: null
    },
    {
        mrsa_id: 3,
        mrsa_name: 'Gamma MRSA',
        risk_level: 'High-Risk',
        last_review_date: '2024-10-01',
        next_due_date: '2024-12-15',
        status: 'UPCOMING',
        days_until_due: 10,
        owner: { user_id: 1, full_name: 'Alice Owner', email: 'alice@example.com' },
        has_exception: true,
        exception_due_date: '2025-02-15'
    },
];

describe('MRSAReviewDashboardWidget', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('renders summary cards and rows', async () => {
        mockGet.mockResolvedValueOnce({ data: sampleStatuses });
        render(<MRSAReviewDashboardWidget />);

        await waitFor(() => {
            expect(screen.getByText('MRSA Review Status')).toBeInTheDocument();
        });

        expect(screen.getByRole('button', { name: /Needs Attention/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Upcoming/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Current/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Total MRSAs/i })).toBeInTheDocument();

        expect(screen.getByText('Alpha MRSA')).toBeInTheDocument();
        expect(screen.getByText('Beta MRSA')).toBeInTheDocument();
        expect(screen.getByText('Gamma MRSA')).toBeInTheDocument();
        const overdueRow = screen.getByText('Beta MRSA').closest('tr');
        const upcomingRow = screen.getByText('Gamma MRSA').closest('tr');
        expect(overdueRow).not.toBeNull();
        expect(upcomingRow).not.toBeNull();
        expect(within(overdueRow as HTMLElement).getByText('Overdue')).toBeInTheDocument();
        expect(within(upcomingRow as HTMLElement).getByText('Upcoming')).toBeInTheDocument();
    });

    it('filters to upcoming items', async () => {
        mockGet.mockResolvedValueOnce({ data: sampleStatuses });
        render(<MRSAReviewDashboardWidget />);

        await waitFor(() => {
            expect(screen.getByText('Beta MRSA')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: /Upcoming/i }));

        expect(screen.getByText('Gamma MRSA')).toBeInTheDocument();
        expect(screen.queryByText('Beta MRSA')).not.toBeInTheDocument();
    });

    it('filters to owned MRSAs when ownerId provided', async () => {
        mockGet.mockResolvedValueOnce({ data: sampleStatuses });
        render(<MRSAReviewDashboardWidget ownerId={1} showOwnerColumn={false} />);

        await waitFor(() => {
            expect(screen.getByText('MRSA Review Status')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: /Total MRSAs/i }));

        expect(screen.getByText('Alpha MRSA')).toBeInTheDocument();
        expect(screen.getByText('Gamma MRSA')).toBeInTheDocument();
        expect(screen.queryByText('Beta MRSA')).not.toBeInTheDocument();
    });
});

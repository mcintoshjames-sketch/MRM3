import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
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

        fireEvent.click(screen.getByRole('button', { name: /All/i }));

        expect(screen.getByText('Alpha MRSA')).toBeInTheDocument();
        expect(screen.getByText('Beta MRSA')).toBeInTheDocument();
        expect(screen.getByText('Gamma MRSA')).toBeInTheDocument();
        expect(screen.getAllByText('Overdue')).toHaveLength(2);
        expect(screen.getAllByText('Upcoming')).toHaveLength(2);
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

        fireEvent.click(screen.getByRole('button', { name: /All/i }));

        expect(screen.getByText('Alpha MRSA')).toBeInTheDocument();
        expect(screen.getByText('Gamma MRSA')).toBeInTheDocument();
        expect(screen.queryByText('Beta MRSA')).not.toBeInTheDocument();
    });
});

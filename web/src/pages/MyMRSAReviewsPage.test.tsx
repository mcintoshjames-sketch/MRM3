import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import MyMRSAReviewsPage from './MyMRSAReviewsPage';

const mockGet = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

vi.mock('../components/Layout', () => ({
    default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

describe('MyMRSAReviewsPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('renders the MRSA reviews heading and widget', async () => {
        mockGet.mockResolvedValueOnce({ data: [] });

        render(<MyMRSAReviewsPage />);

        expect(screen.getByText('My MRSA Reviews')).toBeInTheDocument();

        await waitFor(() => {
            expect(screen.getByText('MRSA Review Status')).toBeInTheDocument();
        });

        expect(mockGet).toHaveBeenCalledWith('/irps/mrsa-review-status');
    });
});

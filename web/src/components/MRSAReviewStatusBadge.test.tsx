import { describe, it, expect } from 'vitest';
import { render, screen } from '../test/utils';
import MRSAReviewStatusBadge from './MRSAReviewStatusBadge';

describe('MRSAReviewStatusBadge', () => {
    it('renders label for known status', () => {
        render(<MRSAReviewStatusBadge status="OVERDUE" />);
        expect(screen.getByText('Overdue')).toBeInTheDocument();
    });

    it('renders unknown status as-is', () => {
        render(<MRSAReviewStatusBadge status="CUSTOM_STATUS" />);
        expect(screen.getByText('CUSTOM_STATUS')).toBeInTheDocument();
    });
});

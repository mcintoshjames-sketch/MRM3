import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import TaxonomyPage from './TaxonomyPage';
import api from '../api/client';

// Mock the API client
vi.mock('../api/client', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

// Mock the AuthContext
vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: { name: 'Test User', email: 'test@example.com' },
        logout: vi.fn(),
        loading: false,
    }),
}));

describe('TaxonomyPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the page title', async () => {
        (api.get as any).mockResolvedValue({ data: [] });
        render(<TaxonomyPage />);

        await waitFor(() => {
            expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        });

        expect(screen.getByText('Taxonomy Management')).toBeInTheDocument();
    });

    it('switches to Model Type Taxonomy tab', async () => {
        (api.get as any).mockResolvedValue({ data: [] });
        render(<TaxonomyPage />);

        await waitFor(() => {
            expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        });

        const modelTypeTab = screen.getByText('Model Type Taxonomy');
        fireEvent.click(modelTypeTab);

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/model-types/categories');
        });
    });

    it('displays model categories and handles layout correctly', async () => {
        const mockCategories = [
            {
                category_id: 1,
                name: 'Risk Category',
                description: 'Risk classification',
                sort_order: 1,
                model_types: []
            }
        ];

        (api.get as any).mockImplementation((url: string) => {
            if (url === '/model-types/categories') {
                return Promise.resolve({ data: mockCategories });
            }
            return Promise.resolve({ data: [] });
        });

        render(<TaxonomyPage />);

        await waitFor(() => {
            expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        });

        // Switch to Model Type tab
        fireEvent.click(screen.getByText('Model Type Taxonomy'));

        await waitFor(() => {
            expect(screen.getByText('Risk Category')).toBeInTheDocument();
        });

        // Check for the description which should be visible
        expect(screen.getByText('Risk classification')).toBeInTheDocument();

        // Check for the "Add Model Type" button
        expect(screen.getByText('+ Add Model Type')).toBeInTheDocument();
    });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import ModelOverlaysTab from './ModelOverlaysTab';

const mockList = vi.fn();
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockRetire = vi.fn();

vi.mock('../api/modelOverlays', () => ({
    listModelOverlays: (...args: any[]) => mockList(...args),
    createModelOverlay: (...args: any[]) => mockCreate(...args),
    updateModelOverlay: (...args: any[]) => mockUpdate(...args),
    retireModelOverlay: (...args: any[]) => mockRetire(...args),
}));

const mockGet = vi.fn();
vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: {
            user_id: 1,
            email: 'validator@example.com',
            full_name: 'Validator User',
            role: 'Validator',
            role_code: 'VALIDATOR',
        },
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
    }),
}));

describe('ModelOverlaysTab', () => {
    beforeEach(() => {
        mockList.mockReset();
        mockCreate.mockReset();
        mockUpdate.mockReset();
        mockRetire.mockReset();
        mockGet.mockReset();
        mockGet.mockResolvedValue({ data: [] });
    });

    it('renders empty state when no overlays exist', async () => {
        mockList.mockResolvedValue([]);
        render(<ModelOverlaysTab modelId={1} />);

        await waitFor(() => {
            expect(screen.getByText('No overlays recorded')).toBeInTheDocument();
        });
    });

    it('renders in-effect overlays by default', async () => {
        mockList.mockResolvedValue([
            {
                overlay_id: 1,
                model_id: 1,
                overlay_kind: 'OVERLAY',
                is_underperformance_related: true,
                description: 'Active overlay',
                rationale: 'Active rationale',
                effective_from: '2020-01-01',
                effective_to: null,
                is_retired: false,
                created_at: '2024-01-01T00:00:00Z',
            },
            {
                overlay_id: 2,
                model_id: 1,
                overlay_kind: 'OVERLAY',
                is_underperformance_related: true,
                description: 'Expired overlay',
                rationale: 'Expired rationale',
                effective_from: '2020-01-01',
                effective_to: '2020-01-15',
                is_retired: false,
                created_at: '2024-01-01T00:00:00Z',
            },
        ]);

        render(<ModelOverlaysTab modelId={1} />);

        await waitFor(() => {
            expect(screen.getByText('Active overlay')).toBeInTheDocument();
        });
        expect(screen.queryByText('Expired overlay')).not.toBeInTheDocument();
    });

    it('includes retired overlays when toggle is enabled', async () => {
        mockList.mockImplementation((_modelId: number, params?: { include_retired?: boolean }) => {
            if (params?.include_retired) {
                return Promise.resolve([
                    {
                        overlay_id: 3,
                        model_id: 1,
                        overlay_kind: 'MANAGEMENT_JUDGEMENT',
                        is_underperformance_related: true,
                        description: 'Retired overlay',
                        rationale: 'Retired rationale',
                        effective_from: '2020-01-01',
                        effective_to: null,
                        is_retired: true,
                        created_at: '2024-01-01T00:00:00Z',
                    },
                ]);
            }
            return Promise.resolve([]);
        });

        render(<ModelOverlaysTab modelId={1} />);

        await waitFor(() => {
            expect(screen.getByText('No overlays recorded')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('checkbox', { name: /include retired/i }));

        await waitFor(() => {
            expect(screen.getByText('Retired overlay')).toBeInTheDocument();
        });
    });

    it('validates required fields before creating overlay', async () => {
        mockList.mockResolvedValue([]);
        render(<ModelOverlaysTab modelId={1} />);

        await waitFor(() => {
            expect(screen.getByText('No overlays recorded')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: /\+ add overlay/i }));
        fireEvent.click(screen.getByRole('button', { name: /save overlay/i }));

        await waitFor(() => {
            expect(screen.getByText(/description, rationale, and effective from date are required/i)).toBeInTheDocument();
        });
        expect(mockCreate).not.toHaveBeenCalled();
    });
});

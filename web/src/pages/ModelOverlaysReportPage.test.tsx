import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '../test/utils';

const mockGet = vi.fn();
vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

vi.mock('../components/Layout', () => ({
    default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import ModelOverlaysReportPage from './ModelOverlaysReportPage';

describe('ModelOverlaysReportPage', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('renders table from API payload', async () => {
        mockGet.mockImplementation((url: string) => {
            if (url === '/reports/model-overlays') {
                return Promise.resolve({
                    data: {
                        filters_applied: {},
                        total_count: 1,
                        items: [
                            {
                                overlay_id: 1,
                                model_id: 10,
                                model_name: 'Alpha Model',
                                model_status: 'Active',
                                risk_tier: 'Tier 1 (High)',
                                team_name: 'Risk Team',
                                overlay_kind: 'OVERLAY',
                                is_underperformance_related: true,
                                description: 'Overlay description',
                                rationale: 'Overlay rationale',
                                effective_from: '2025-01-01',
                                effective_to: null,
                                region_name: 'North America',
                                evidence_description: null,
                                has_monitoring_traceability: false,
                                created_at: '2025-01-02T00:00:00Z',
                            },
                        ],
                    },
                });
            }
            if (url === '/regions/') return Promise.resolve({ data: [] });
            if (url === '/teams/') return Promise.resolve({ data: [] });
            if (url.startsWith('/taxonomies/by-names/')) {
                return Promise.resolve({ data: [{ name: 'Model Risk Tier', values: [] }] });
            }
            return Promise.resolve({ data: [] });
        });

        render(<ModelOverlaysReportPage />);

        await waitFor(() => {
            expect(screen.getByText('Alpha Model')).toBeInTheDocument();
        });
    });

    it('filters trigger refetch and update rows', async () => {
        mockGet.mockImplementation((url: string, options?: { params?: Record<string, unknown> }) => {
            if (url === '/reports/model-overlays') {
                if (options?.params?.overlay_kind === 'MANAGEMENT_JUDGEMENT') {
                    return Promise.resolve({
                        data: {
                            filters_applied: {},
                            total_count: 1,
                            items: [
                                {
                                    overlay_id: 2,
                                    model_id: 20,
                                    model_name: 'Beta Model',
                                    model_status: 'Active',
                                    risk_tier: 'Tier 2 (Medium)',
                                    team_name: 'Validation Team',
                                    overlay_kind: 'MANAGEMENT_JUDGEMENT',
                                    is_underperformance_related: true,
                                    description: 'Judgement description',
                                    rationale: 'Judgement rationale',
                                    effective_from: '2025-02-01',
                                    effective_to: null,
                                    region_name: null,
                                    evidence_description: null,
                                    has_monitoring_traceability: true,
                                    created_at: '2025-02-02T00:00:00Z',
                                },
                            ],
                        },
                    });
                }
                return Promise.resolve({
                    data: {
                        filters_applied: {},
                        total_count: 1,
                        items: [
                            {
                                overlay_id: 1,
                                model_id: 10,
                                model_name: 'Alpha Model',
                                model_status: 'Active',
                                risk_tier: 'Tier 1 (High)',
                                team_name: 'Risk Team',
                                overlay_kind: 'OVERLAY',
                                is_underperformance_related: true,
                                description: 'Overlay description',
                                rationale: 'Overlay rationale',
                                effective_from: '2025-01-01',
                                effective_to: null,
                                region_name: 'North America',
                                evidence_description: null,
                                has_monitoring_traceability: false,
                                created_at: '2025-01-02T00:00:00Z',
                            },
                        ],
                    },
                });
            }
            if (url === '/regions/') return Promise.resolve({ data: [] });
            if (url === '/teams/') return Promise.resolve({ data: [] });
            if (url.startsWith('/taxonomies/by-names/')) {
                return Promise.resolve({ data: [{ name: 'Model Risk Tier', values: [] }] });
            }
            return Promise.resolve({ data: [] });
        });

        render(<ModelOverlaysReportPage />);

        await waitFor(() => {
            expect(screen.getByText('Alpha Model')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText('Overlay Kind'), { target: { value: 'MANAGEMENT_JUDGEMENT' } });

        await waitFor(() => {
            expect(screen.getByText('Beta Model')).toBeInTheDocument();
        });
    });
});

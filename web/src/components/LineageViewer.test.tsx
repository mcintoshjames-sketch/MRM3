import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '../test/utils';
import LineageViewer from './LineageViewer';

// Mock the API client
const mockGet = vi.fn();
vi.mock('../api/client', () => ({
    default: {
        get: (...args: any[]) => mockGet(...args),
    },
}));

const sampleLineageData = {
    model: {
        model_id: 1,
        model_name: 'Center Model',
    },
    upstream: [
        {
            model_id: 2,
            model_name: 'Feeder Model',
            dependency_type: 'INPUT_DATA',
            description: 'Provides raw data',
            depth: 1,
            upstream: [
                {
                    model_id: 3,
                    model_name: 'Grandparent Model',
                    dependency_type: 'SCORE',
                    description: null,
                    depth: 2,
                    upstream: []
                }
            ]
        }
    ],
    downstream: [
        {
            model_id: 4,
            model_name: 'Consumer Model',
            dependency_type: 'SCORE',
            description: 'Uses score for decision',
            depth: 1,
            downstream: []
        }
    ]
};

describe('LineageViewer', () => {
    beforeEach(() => {
        mockGet.mockReset();
    });

    it('displays loading state initially', () => {
        mockGet.mockImplementation(() => new Promise(() => { }));
        render(<LineageViewer modelId={1} modelName="Center Model" />);
        expect(screen.getByText('Loading lineage data...')).toBeInTheDocument();
    });

    it('displays error state on failure', async () => {
        mockGet.mockRejectedValue({ response: { data: { detail: 'API Error' } } });
        render(<LineageViewer modelId={1} modelName="Center Model" />);
        await waitFor(() => {
            expect(screen.getByText('Error Loading Lineage')).toBeInTheDocument();
            expect(screen.getByText('API Error')).toBeInTheDocument();
        });
    });

    it('renders lineage tree correctly', async () => {
        mockGet.mockResolvedValue({ data: sampleLineageData });
        render(<LineageViewer modelId={1} modelName="Center Model" />);

        await waitFor(() => {
            // Check center model
            expect(screen.getByText('Center Model')).toBeInTheDocument();

            // Check upstream section
            expect(screen.getByText('Upstream Dependencies (Feeders)')).toBeInTheDocument();
            expect(screen.getByText('Feeder Model')).toBeInTheDocument();
            expect(screen.getByText('Grandparent Model')).toBeInTheDocument();
            expect(screen.getByText('INPUT_DATA')).toBeInTheDocument();

            // Check downstream section
            expect(screen.getByText('Downstream Dependencies (Consumers)')).toBeInTheDocument();
            expect(screen.getByText('Consumer Model')).toBeInTheDocument();

            // Check export button
            expect(screen.getByText('Export PDF')).toBeInTheDocument();
        });
    }); it('handles empty lineage', async () => {
        mockGet.mockResolvedValue({
            data: {
                model: { model_id: 1, model_name: 'Center Model' },
                upstream: [],
                downstream: []
            }
        });
        render(<LineageViewer modelId={1} modelName="Center Model" />);

        await waitFor(() => {
            expect(screen.getByText('No Dependency Lineage')).toBeInTheDocument();
        });
    });

    it('updates when controls change', async () => {
        mockGet.mockResolvedValue({ data: sampleLineageData });
        render(<LineageViewer modelId={1} modelName="Center Model" />);

        await waitFor(() => {
            expect(screen.getByText('Center Model')).toBeInTheDocument();
        });

        // Change direction
        fireEvent.change(screen.getByLabelText('Direction'), {
            target: { value: 'upstream' }
        });

        await waitFor(() => {
            expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('direction=upstream'));
        });
    });
});

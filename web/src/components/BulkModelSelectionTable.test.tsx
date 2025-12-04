import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../test/utils';
import BulkModelSelectionTable from './BulkModelSelectionTable';
import { BulkAttestationModel } from '../hooks/useBulkAttestation';

const samplePendingModels: BulkAttestationModel[] = [
    {
        attestation_id: 1,
        model_id: 10,
        model_name: 'Credit Risk Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15T00:00:00Z',
        attestation_status: 'PENDING',
        is_excluded: false,
    },
    {
        attestation_id: 2,
        model_id: 20,
        model_name: 'Fraud Detection Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15T00:00:00Z',
        attestation_status: 'PENDING',
        is_excluded: true,
    },
    {
        attestation_id: 3,
        model_id: 30,
        model_name: 'Pricing Model',
        risk_tier_code: 'T2',
        risk_tier_label: 'Tier 2',
        model_status: 'Active',
        last_attested_date: null,
        attestation_status: 'PENDING',
        is_excluded: false,
    },
];

const mixedStatusModels: BulkAttestationModel[] = [
    ...samplePendingModels,
    {
        attestation_id: 4,
        model_id: 40,
        model_name: 'Already Submitted Model',
        risk_tier_code: 'T2',
        risk_tier_label: 'Tier 2',
        model_status: 'Active',
        last_attested_date: '2024-06-01T00:00:00Z',
        attestation_status: 'SUBMITTED',
        is_excluded: false,
    },
    {
        attestation_id: 5,
        model_id: 50,
        model_name: 'Accepted Model',
        risk_tier_code: 'T3',
        risk_tier_label: 'Tier 3',
        model_status: 'Active',
        last_attested_date: '2024-06-01T00:00:00Z',
        attestation_status: 'ACCEPTED',
        is_excluded: false,
    },
];

describe('BulkModelSelectionTable', () => {
    const mockToggleModel = vi.fn();
    const mockSelectAll = vi.fn();
    const mockDeselectAll = vi.fn();

    const defaultProps = {
        models: samplePendingModels,
        selectedModelIds: new Set([10, 30]), // Model 20 is excluded
        onToggleModel: mockToggleModel,
        onSelectAll: mockSelectAll,
        onDeselectAll: mockDeselectAll,
    };

    beforeEach(() => {
        mockToggleModel.mockReset();
        mockSelectAll.mockReset();
        mockDeselectAll.mockReset();
    });

    describe('rendering', () => {
        it('renders table with model names', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
            expect(screen.getByText('Fraud Detection Model')).toBeInTheDocument();
            expect(screen.getByText('Pricing Model')).toBeInTheDocument();
        });

        it('renders risk tier labels', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getAllByText('Tier 1')).toHaveLength(2);
            expect(screen.getByText('Tier 2')).toBeInTheDocument();
        });

        it('renders last attested dates in ISO format', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getAllByText('2024-06-15')).toHaveLength(2);
            expect(screen.getByText('-')).toBeInTheDocument(); // Model with null date
        });

        it('renders table headers', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getByText('Model Name')).toBeInTheDocument();
            expect(screen.getByText('Risk Tier')).toBeInTheDocument();
            expect(screen.getByText('Status')).toBeInTheDocument();
            expect(screen.getByText('Last Attested')).toBeInTheDocument();
        });

        it('renders selection count in header', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getByText('2 of 3 selected')).toBeInTheDocument();
        });

        it('shows empty state when no pending models', () => {
            render(
                <BulkModelSelectionTable
                    {...defaultProps}
                    models={[]}
                    selectedModelIds={new Set()}
                />
            );

            expect(screen.getByText('No pending models available for bulk attestation.')).toBeInTheDocument();
        });

        it('only shows PENDING models in table', () => {
            render(
                <BulkModelSelectionTable
                    {...defaultProps}
                    models={mixedStatusModels}
                />
            );

            // Only PENDING models should be shown
            expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
            expect(screen.getByText('Fraud Detection Model')).toBeInTheDocument();
            expect(screen.getByText('Pricing Model')).toBeInTheDocument();

            // SUBMITTED and ACCEPTED models should NOT be shown
            expect(screen.queryByText('Already Submitted Model')).not.toBeInTheDocument();
            expect(screen.queryByText('Accepted Model')).not.toBeInTheDocument();
        });
    });

    describe('status badges', () => {
        it('shows Excluded badge for unselected models', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            // Model 20 is not in selectedModelIds, so it should show Excluded
            const excludedBadges = screen.getAllByText('Excluded');
            expect(excludedBadges).toHaveLength(1);
        });

        it('shows Pending badge for selected models', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            // Models 10 and 30 are selected, should show Pending
            const pendingBadges = screen.getAllByText('Pending');
            expect(pendingBadges).toHaveLength(2);
        });
    });

    describe('row highlighting', () => {
        it('applies orange background to excluded rows', () => {
            const { container } = render(<BulkModelSelectionTable {...defaultProps} />);

            // Find all table rows in tbody
            const tableBody = container.querySelector('tbody');
            const rows = tableBody?.querySelectorAll('tr') || [];

            // Model 20 (index 1) should have orange background
            expect(rows[1]?.className).toContain('bg-orange-50');

            // Models 10 and 30 (indices 0 and 2) should not have orange background
            expect(rows[0]?.className).not.toContain('bg-orange-50');
            expect(rows[2]?.className).not.toContain('bg-orange-50');
        });
    });

    describe('checkboxes', () => {
        it('shows checked checkbox for selected models', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];

            // Model 10 (index 0) - selected
            expect(checkboxes[0].checked).toBe(true);

            // Model 20 (index 1) - excluded
            expect(checkboxes[1].checked).toBe(false);

            // Model 30 (index 2) - selected
            expect(checkboxes[2].checked).toBe(true);
        });

        it('disables checkboxes when disabled prop is true', () => {
            render(<BulkModelSelectionTable {...defaultProps} disabled={true} />);

            const checkboxes = screen.getAllByRole('checkbox');
            checkboxes.forEach((checkbox) => {
                expect(checkbox).toBeDisabled();
            });
        });
    });

    describe('selection actions', () => {
        it('calls onToggleModel when checkbox clicked', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]); // Click on model 20

            expect(mockToggleModel).toHaveBeenCalledWith(20);
        });

        it('calls onToggleModel when row clicked', () => {
            const { container } = render(<BulkModelSelectionTable {...defaultProps} />);

            const tableBody = container.querySelector('tbody');
            const rows = tableBody?.querySelectorAll('tr') || [];

            fireEvent.click(rows[0]); // Click on first row (model 10)

            expect(mockToggleModel).toHaveBeenCalledWith(10);
        });

        it('does not call onToggleModel when row clicked and disabled', () => {
            const { container } = render(
                <BulkModelSelectionTable {...defaultProps} disabled={true} />
            );

            const tableBody = container.querySelector('tbody');
            const rows = tableBody?.querySelectorAll('tr') || [];

            fireEvent.click(rows[0]);

            expect(mockToggleModel).not.toHaveBeenCalled();
        });

        it('calls onSelectAll when Select All button clicked', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const selectAllButton = screen.getByText(/Select All/);
            fireEvent.click(selectAllButton);

            expect(mockSelectAll).toHaveBeenCalled();
        });

        it('calls onDeselectAll when Deselect All button clicked', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const deselectAllButton = screen.getByText('Deselect All');
            fireEvent.click(deselectAllButton);

            expect(mockDeselectAll).toHaveBeenCalled();
        });
    });

    describe('Select All button states', () => {
        it('disables Select All when all models already selected', () => {
            render(
                <BulkModelSelectionTable
                    {...defaultProps}
                    selectedModelIds={new Set([10, 20, 30])} // All selected
                />
            );

            const selectAllButton = screen.getByText(/Select All/);
            expect(selectAllButton).toBeDisabled();
        });

        it('disables Deselect All when no models selected', () => {
            render(
                <BulkModelSelectionTable
                    {...defaultProps}
                    selectedModelIds={new Set()} // None selected
                />
            );

            const deselectAllButton = screen.getByText('Deselect All');
            expect(deselectAllButton).toBeDisabled();
        });

        it('disables Select All when disabled prop is true', () => {
            render(<BulkModelSelectionTable {...defaultProps} disabled={true} />);

            const selectAllButton = screen.getByText(/Select All/);
            expect(selectAllButton).toBeDisabled();
        });
    });

    describe('summary footer', () => {
        it('shows selected count in footer', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getByText('2 selected for bulk attestation')).toBeInTheDocument();
        });

        it('shows excluded count when models are excluded', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            expect(screen.getByText('1 excluded (require individual attestation)')).toBeInTheDocument();
        });

        it('does not show excluded message when all models selected', () => {
            render(
                <BulkModelSelectionTable
                    {...defaultProps}
                    selectedModelIds={new Set([10, 20, 30])}
                />
            );

            expect(screen.queryByText(/excluded \(require individual attestation\)/)).not.toBeInTheDocument();
        });
    });

    describe('model links', () => {
        it('renders model names as links to model details', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const creditRiskLink = screen.getByRole('link', { name: 'Credit Risk Model' });
            expect(creditRiskLink).toHaveAttribute('href', '/models/10');

            const fraudDetectionLink = screen.getByRole('link', { name: 'Fraud Detection Model' });
            expect(fraudDetectionLink).toHaveAttribute('href', '/models/20');
        });

        it('clicking link does not trigger row toggle', () => {
            render(<BulkModelSelectionTable {...defaultProps} />);

            const creditRiskLink = screen.getByRole('link', { name: 'Credit Risk Model' });
            fireEvent.click(creditRiskLink);

            // Link click should stop propagation, so toggle should not be called
            expect(mockToggleModel).not.toHaveBeenCalled();
        });
    });
});

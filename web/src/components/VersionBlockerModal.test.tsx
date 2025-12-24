import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../test/utils';
import VersionBlockerModal, { VersionBlocker } from './VersionBlockerModal';

describe('VersionBlockerModal', () => {
    const mockOnClose = vi.fn();
    const mockOnSelectVersion = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    const noDraftBlocker: VersionBlocker = {
        type: 'NO_DRAFT_VERSION',
        severity: 'error',
        model_id: 1,
        model_name: 'Credit Risk Scorecard',
        message: 'Model "Credit Risk Scorecard" has no DRAFT version available for validation.'
    };

    const missingVersionBlocker: VersionBlocker = {
        type: 'MISSING_VERSION_LINK',
        severity: 'warning',
        model_id: 2,
        model_name: 'ALM Model',
        message: 'Model "ALM Model" requires a version to be linked for CHANGE validation.',
        available_versions: [
            { version_id: 101, version_number: '2.1', change_description: 'Updated risk parameters' },
            { version_id: 102, version_number: '2.2', change_description: 'Performance improvements' }
        ]
    };

    describe('Header', () => {
        it('renders the modal header with correct title', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('Cannot Create CHANGE Validation')).toBeInTheDocument();
        });

        it('renders the explanation text', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('CHANGE validations require each model to be linked to a specific version')).toBeInTheDocument();
        });
    });

    describe('NO_DRAFT_VERSION blockers', () => {
        it('displays the NO DRAFT VERSION section when blockers exist', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('NO DRAFT VERSION')).toBeInTheDocument();
        });

        it('displays the blocker count', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('(1)')).toBeInTheDocument();
        });

        it('displays the model name', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('Credit Risk Scorecard')).toBeInTheDocument();
        });

        it('displays the blocker message', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('Model "Credit Risk Scorecard" has no DRAFT version available for validation.')).toBeInTheDocument();
        });

        it('renders link to model versions page', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            const link = screen.getByRole('link', { name: /Submit Model Change/i });
            expect(link).toHaveAttribute('href', '/models/1?tab=versions');
        });

        it('shows action required message in footer', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText(/Action required:/)).toBeInTheDocument();
        });
    });

    describe('MISSING_VERSION_LINK blockers', () => {
        it('displays the VERSION NOT SELECTED section when blockers exist', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('VERSION NOT SELECTED')).toBeInTheDocument();
        });

        it('displays the blocker count', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('(1)')).toBeInTheDocument();
        });

        it('displays the model name', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('ALM Model')).toBeInTheDocument();
        });

        it('displays version selection dropdown with available versions', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            const dropdown = screen.getByRole('combobox');
            expect(dropdown).toBeInTheDocument();
            expect(screen.getByText('Choose a version...')).toBeInTheDocument();
        });

        it('displays version options with version numbers and descriptions', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('2.1 - Updated risk parameters')).toBeInTheDocument();
            expect(screen.getByText('2.2 - Performance improvements')).toBeInTheDocument();
        });

        it('calls onSelectVersion when a version is selected', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            const dropdown = screen.getByRole('combobox');
            fireEvent.change(dropdown, { target: { value: '101' } });
            expect(mockOnSelectVersion).toHaveBeenCalledWith(2, 101);
        });

        it('shows select versions message in footer when no NO_DRAFT blockers', () => {
            render(
                <VersionBlockerModal
                    blockers={[missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText(/Select versions above/)).toBeInTheDocument();
        });
    });

    describe('Mixed blockers', () => {
        it('displays both blocker types when present', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker, missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText('NO DRAFT VERSION')).toBeInTheDocument();
            expect(screen.getByText('VERSION NOT SELECTED')).toBeInTheDocument();
        });

        it('displays correct counts for each blocker type', () => {
            const blockers: VersionBlocker[] = [
                noDraftBlocker,
                { ...noDraftBlocker, model_id: 3, model_name: 'Fraud Model' },
                missingVersionBlocker
            ];
            render(
                <VersionBlockerModal
                    blockers={blockers}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            // Should show (2) for NO_DRAFT and (1) for MISSING_VERSION
            const counts = screen.getAllByText(/\(\d+\)/);
            expect(counts).toHaveLength(2);
            expect(screen.getByText('(2)')).toBeInTheDocument();
            expect(screen.getByText('(1)')).toBeInTheDocument();
        });

        it('shows action required message when NO_DRAFT blockers present', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker, missingVersionBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.getByText(/Action required:/)).toBeInTheDocument();
        });
    });

    describe('Close behavior', () => {
        it('calls onClose when header close button is clicked', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            // Find the close button in header (first button with svg icon)
            const closeButtons = screen.getAllByRole('button');
            // First button is the X close, last button is "Close" text button
            fireEvent.click(closeButtons[0]);
            expect(mockOnClose).toHaveBeenCalledTimes(1);
        });

        it('calls onClose when footer Close button is clicked', () => {
            render(
                <VersionBlockerModal
                    blockers={[noDraftBlocker]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            const closeButton = screen.getByRole('button', { name: 'Close' });
            fireEvent.click(closeButton);
            expect(mockOnClose).toHaveBeenCalledTimes(1);
        });
    });

    describe('Empty available versions', () => {
        it('does not show dropdown when available_versions is empty', () => {
            const blockerWithNoVersions: VersionBlocker = {
                ...missingVersionBlocker,
                available_versions: []
            };
            render(
                <VersionBlockerModal
                    blockers={[blockerWithNoVersions]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
        });

        it('does not show dropdown when available_versions is undefined', () => {
            const blockerWithUndefinedVersions: VersionBlocker = {
                type: 'MISSING_VERSION_LINK',
                severity: 'warning',
                model_id: 2,
                model_name: 'ALM Model',
                message: 'Model "ALM Model" requires a version to be linked.'
            };
            render(
                <VersionBlockerModal
                    blockers={[blockerWithUndefinedVersions]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
        });
    });

    describe('Long description truncation', () => {
        it('truncates long change descriptions with ellipsis', () => {
            const blockerWithLongDescription: VersionBlocker = {
                ...missingVersionBlocker,
                available_versions: [
                    {
                        version_id: 103,
                        version_number: '3.0',
                        change_description: 'This is a very long change description that exceeds fifty characters and should be truncated'
                    }
                ]
            };
            render(
                <VersionBlockerModal
                    blockers={[blockerWithLongDescription]}
                    onClose={mockOnClose}
                    onSelectVersion={mockOnSelectVersion}
                />
            );
            // First 50 chars + ellipsis
            expect(screen.getByText(/3\.0 - This is a very long change description that exceed\.\.\./)).toBeInTheDocument();
        });
    });
});

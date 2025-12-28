import React from 'react';

interface FilterStatusBarProps {
    activeFilterLabel: string;
    onClear: () => void;
    entityName?: string;
}

const FilterStatusBar: React.FC<FilterStatusBarProps> = ({
    activeFilterLabel,
    onClear,
    entityName = 'items',
}) => {
    if (!activeFilterLabel) {
        return null;
    }

    return (
        <div className="mb-4 flex flex-wrap items-center gap-3">
            <span className="text-sm text-gray-600">
                Showing: <strong>{activeFilterLabel}</strong> {entityName}
            </span>
            <button type="button" onClick={onClear} className="btn-secondary text-sm">
                Clear filters
            </button>
        </div>
    );
};

export default FilterStatusBar;

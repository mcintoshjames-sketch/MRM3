import { useState, useRef, useEffect } from 'react';

interface Option {
    value: string | number;
    label: string;
    searchText?: string;
    secondaryLabel?: string;
}

interface MultiSelectDropdownProps {
    options: Option[];
    selectedValues: (string | number)[];
    onChange: (selectedValues: (string | number)[]) => void;
    placeholder?: string;
    label?: string;
}

export default function MultiSelectDropdown({
    options,
    selectedValues,
    onChange,
    placeholder = 'Select...',
    label
}: MultiSelectDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setSearchTerm('');
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const normalizedSearch = searchTerm.toLowerCase();
    const filteredOptions = options.filter(option => {
        const haystack = (option.searchText || option.label).toLowerCase();
        return haystack.includes(normalizedSearch);
    });

    const toggleOption = (value: string | number) => {
        if (selectedValues.includes(value)) {
            onChange(selectedValues.filter(v => v !== value));
        } else {
            onChange([...selectedValues, value]);
        }
    };

    const removeOption = (value: string | number) => {
        onChange(selectedValues.filter(v => v !== value));
    };

    const getSelectedLabels = () => {
        return selectedValues
            .map(value => options.find(opt => opt.value === value)?.label)
            .filter(Boolean) as string[];
    };

    return (
        <div ref={dropdownRef} className="relative">
            {label && (
                <label className="block text-xs font-medium text-gray-700 mb-1">
                    {label}
                </label>
            )}

            {/* Selected items as tags */}
            {selectedValues.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                    {getSelectedLabels().map((label, index) => (
                        <span
                            key={index}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded"
                        >
                            {label}
                            <button
                                type="button"
                                onClick={() => removeOption(selectedValues[index])}
                                className="hover:text-blue-900"
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}

            {/* Dropdown trigger */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full input-field text-sm text-left flex items-center justify-between"
            >
                <span className={selectedValues.length === 0 ? 'text-gray-400' : ''}>
                    {selectedValues.length === 0
                        ? placeholder
                        : `${selectedValues.length} selected`}
                </span>
                <svg
                    className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Dropdown menu */}
            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-hidden">
                    {/* Search box */}
                    <div className="p-2 border-b">
                        <input
                            type="text"
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="Search..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                        />
                    </div>

                    {/* Options list */}
                    <div className="overflow-y-auto max-h-48">
                        {filteredOptions.length === 0 ? (
                            <div className="px-3 py-2 text-sm text-gray-500 text-center">
                                No options found
                            </div>
                        ) : (
                            filteredOptions.map(option => (
                                <label
                                    key={option.value}
                                    className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer"
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedValues.includes(option.value)}
                                        onChange={() => toggleOption(option.value)}
                                        className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="text-sm">
                                        <span className="block">{option.label}</span>
                                        {option.secondaryLabel && (
                                            <span className="block text-xs text-gray-500">{option.secondaryLabel}</span>
                                        )}
                                    </span>
                                </label>
                            ))
                        )}
                    </div>

                    {/* Clear all button */}
                    {selectedValues.length > 0 && (
                        <div className="p-2 border-t">
                            <button
                                type="button"
                                onClick={() => onChange([])}
                                className="w-full text-xs text-red-600 hover:text-red-800"
                            >
                                Clear all
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

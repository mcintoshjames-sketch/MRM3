import { useEffect, useRef, useState } from 'react';

interface ModelOption {
    model_id: number;
    model_name: string;
}

interface SpecialOption {
    value: string;
    label: string;
}

interface ModelSearchSelectProps {
    models: ModelOption[];
    value: number | string | null;
    onChange: (value: number | string | null) => void;
    placeholder?: string;
    disabled?: boolean;
    required?: boolean;
    maxResults?: number;
    showIdInDropdown?: boolean;
    specialOptions?: SpecialOption[];
    disabledValues?: Array<string | number>;
    id?: string;
    inputClassName?: string;
}

export default function ModelSearchSelect({
    models,
    value,
    onChange,
    placeholder = 'Type to search models...',
    disabled = false,
    required = false,
    maxResults = 50,
    showIdInDropdown = true,
    specialOptions = [],
    disabledValues = [],
    id,
    inputClassName = 'input-field'
}: ModelSearchSelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [isEditing, setIsEditing] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const selectedModel = typeof value === 'number'
        ? models.find((model) => model.model_id === value)
        : undefined;
    const selectedSpecial = typeof value === 'string'
        ? specialOptions.find((option) => option.value === value)
        : undefined;
    const selectedLabel = selectedModel?.model_name || selectedSpecial?.label || '';

    useEffect(() => {
        if (isEditing) return;
        setSearchTerm(selectedLabel);
    }, [selectedLabel, isEditing]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setIsEditing(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const disabledSet = new Set(disabledValues);
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const filteredModels = models.filter((model) => {
        if (!normalizedSearch) return true;
        return (
            model.model_name.toLowerCase().includes(normalizedSearch) ||
            String(model.model_id).includes(normalizedSearch)
        );
    }).slice(0, maxResults);

    const handleInputChange = (valueText: string) => {
        setIsEditing(true);
        setSearchTerm(valueText);
        setIsOpen(true);

        if (value !== null) {
            const trimmedValue = valueText.trim();
            const matchesSelected = selectedModel
                ? trimmedValue === selectedModel.model_name || trimmedValue === String(selectedModel.model_id)
                : selectedSpecial
                    ? trimmedValue === selectedSpecial.label
                    : false;
            if (!matchesSelected) {
                onChange(null);
            }
        }

        if (!valueText.trim()) {
            onChange(null);
        }
    };

    const handleSelect = (nextValue: number | string, label: string) => {
        if (disabledSet.has(nextValue)) return;
        onChange(nextValue);
        setIsEditing(false);
        setSearchTerm(label);
        setIsOpen(false);
    };

    return (
        <div ref={containerRef} className="relative">
            <input
                id={id}
                type="text"
                value={searchTerm}
                onChange={(e) => handleInputChange(e.target.value)}
                onFocus={() => {
                    if (disabled) return;
                    setIsOpen(true);
                    setIsEditing(true);
                }}
                placeholder={placeholder}
                className={inputClassName}
                required={required}
                disabled={disabled}
            />
            {isOpen && !disabled && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {specialOptions.length > 0 && (
                        <div className="border-b border-gray-200">
                            {specialOptions.map((option) => (
                                <div
                                    key={option.value}
                                    className={`px-4 py-2 text-sm ${disabledSet.has(option.value)
                                        ? 'text-gray-300 cursor-not-allowed'
                                        : 'hover:bg-gray-100 cursor-pointer'
                                    }`}
                                    onClick={() => handleSelect(option.value, option.label)}
                                >
                                    {option.label}
                                </div>
                            ))}
                        </div>
                    )}
                    {filteredModels.length > 0 ? (
                        filteredModels.map((model) => (
                            <div
                                key={model.model_id}
                                className={`px-4 py-2 text-sm ${disabledSet.has(model.model_id)
                                    ? 'text-gray-300 cursor-not-allowed'
                                    : 'hover:bg-gray-100 cursor-pointer'
                                }`}
                                onClick={() => handleSelect(model.model_id, model.model_name)}
                            >
                                <div className="font-medium">{model.model_name}</div>
                                {showIdInDropdown && (
                                    <div className="text-xs text-gray-500">ID: {model.model_id}</div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="px-4 py-2 text-sm text-gray-500">No models found</div>
                    )}
                </div>
            )}
        </div>
    );
}

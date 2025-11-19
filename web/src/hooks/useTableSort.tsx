import { useState, useMemo } from 'react';

export type SortDirection = 'asc' | 'desc' | null;

interface SortConfig<T> {
    key: keyof T | string;
    direction: SortDirection;
}

export function useTableSort<T>(data: T[], initialKey?: keyof T | string, initialDirection: SortDirection = 'asc') {
    const [sortConfig, setSortConfig] = useState<SortConfig<T>>({
        key: initialKey || '',
        direction: initialDirection
    });

    const sortedData = useMemo(() => {
        if (!sortConfig.key || !sortConfig.direction) return data;

        const sorted = [...data].sort((a, b) => {
            // Handle nested properties (e.g., 'owner.full_name')
            const getNestedValue = (obj: any, path: string) => {
                return path.split('.').reduce((current, key) => current?.[key], obj);
            };

            const aValue = getNestedValue(a, sortConfig.key as string);
            const bValue = getNestedValue(b, sortConfig.key as string);

            // Handle null/undefined values
            if (aValue == null && bValue == null) return 0;
            if (aValue == null) return 1;
            if (bValue == null) return -1;

            // Compare values
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                return sortConfig.direction === 'asc'
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            }

            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return sortConfig.direction === 'asc'
                    ? aValue - bValue
                    : bValue - aValue;
            }

            // Date comparison
            const aDate = new Date(aValue);
            const bDate = new Date(bValue);
            if (!isNaN(aDate.getTime()) && !isNaN(bDate.getTime())) {
                return sortConfig.direction === 'asc'
                    ? aDate.getTime() - bDate.getTime()
                    : bDate.getTime() - aDate.getTime();
            }

            return 0;
        });

        return sorted;
    }, [data, sortConfig]);

    const requestSort = (key: keyof T | string) => {
        let direction: SortDirection = 'asc';

        if (sortConfig.key === key) {
            if (sortConfig.direction === 'asc') {
                direction = 'desc';
            } else if (sortConfig.direction === 'desc') {
                direction = null;
            }
        }

        setSortConfig({ key, direction });
    };

    const getSortIcon = (columnKey: keyof T | string) => {
        if (sortConfig.key !== columnKey) {
            return (
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
            );
        }

        if (sortConfig.direction === 'asc') {
            return (
                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
            );
        }

        if (sortConfig.direction === 'desc') {
            return (
                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            );
        }

        return null;
    };

    return { sortedData, requestSort, getSortIcon, sortConfig };
}

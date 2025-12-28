import React from 'react';

interface StatFilterCardProps {
    label: string;
    count: number;
    isActive: boolean;
    onClick: () => void;
    colorScheme: 'blue' | 'yellow' | 'red' | 'green' | 'gray' | 'purple' | 'orange';
    disabled?: boolean;
}

const colorStyles = {
    blue: { text: 'text-blue-600', ring: 'ring-blue-500', focus: 'focus-visible:ring-blue-500' },
    yellow: { text: 'text-yellow-600', ring: 'ring-yellow-500', focus: 'focus-visible:ring-yellow-500' },
    red: { text: 'text-red-600', ring: 'ring-red-500', focus: 'focus-visible:ring-red-500' },
    green: { text: 'text-green-600', ring: 'ring-green-500', focus: 'focus-visible:ring-green-500' },
    gray: { text: 'text-gray-600', ring: 'ring-gray-400', focus: 'focus-visible:ring-gray-400' },
    purple: { text: 'text-purple-600', ring: 'ring-purple-500', focus: 'focus-visible:ring-purple-500' },
    orange: { text: 'text-orange-600', ring: 'ring-orange-500', focus: 'focus-visible:ring-orange-500' },
};

const StatFilterCard: React.FC<StatFilterCardProps> = ({
    label,
    count,
    isActive,
    onClick,
    colorScheme,
    disabled = false,
}) => {
    const styles = colorStyles[colorScheme];
    const activeClasses = isActive ? `ring-2 ${styles.ring}` : '';
    const interactiveClasses = disabled ? 'cursor-default' : 'cursor-pointer hover:shadow-md';

    return (
        <button
            type="button"
            aria-pressed={isActive}
            disabled={disabled}
            onClick={onClick}
            className={`w-full text-left bg-white p-4 rounded-lg shadow transition-shadow focus-visible:outline-none focus-visible:ring-2 ${styles.focus} ${interactiveClasses} ${activeClasses}`}
        >
            <div className="text-sm text-gray-500">{label}</div>
            <div className={`text-2xl font-bold ${styles.text}`}>{count}</div>
        </button>
    );
};

export default StatFilterCard;

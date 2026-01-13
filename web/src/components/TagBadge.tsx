import React from 'react';
import { getContrastTextColor, DEFAULT_TAG_COLOR } from '../utils/getContrastTextColor';

export interface TagBadgeProps {
  /** Tag name to display */
  name: string;
  /** Background color (hex format, e.g., "#DC2626") */
  color?: string;
  /** Optional click handler for remove button */
  onRemove?: () => void;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

/**
 * A colored tag badge component with auto-calculated text color for WCAG accessibility.
 *
 * Features:
 * - Automatically calculates black or white text based on background luminosity
 * - Optional remove button (X) for tag removal
 * - Two size variants: sm (small) and md (medium)
 */
const TagBadge: React.FC<TagBadgeProps> = ({
  name,
  color = DEFAULT_TAG_COLOR,
  onRemove,
  size = 'sm',
  className = '',
}) => {
  const backgroundColor = color || DEFAULT_TAG_COLOR;
  const textColor = getContrastTextColor(backgroundColor);

  const sizeClasses = size === 'sm'
    ? 'px-2 py-0.5 text-xs'
    : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClasses} ${className}`}
      style={{ backgroundColor, color: textColor }}
    >
      <span className="truncate max-w-[150px]" title={name}>
        {name}
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 hover:opacity-75 focus:outline-none"
          title={`Remove ${name}`}
        >
          <svg
            className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </span>
  );
};

export default TagBadge;

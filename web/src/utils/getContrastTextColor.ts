/**
 * Calculate the appropriate text color (black or white) for WCAG-compliant contrast
 * against a given background color.
 *
 * Uses relative luminance calculation per WCAG 2.0 guidelines.
 *
 * @param hexColor - Background color in hex format (e.g., "#DC2626")
 * @returns "#000000" for light backgrounds, "#FFFFFF" for dark backgrounds
 */
export function getContrastTextColor(hexColor: string): string {
  // Default to white text if invalid color
  if (!hexColor || !hexColor.startsWith('#') || hexColor.length !== 7) {
    return '#FFFFFF';
  }

  // Parse hex color to RGB
  const r = parseInt(hexColor.slice(1, 3), 16) / 255;
  const g = parseInt(hexColor.slice(3, 5), 16) / 255;
  const b = parseInt(hexColor.slice(5, 7), 16) / 255;

  // Calculate relative luminance using sRGB formula
  // https://www.w3.org/TR/WCAG20/#relativeluminancedef
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;

  // Use black text for light backgrounds (luminance > 0.5)
  // Use white text for dark backgrounds (luminance <= 0.5)
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
}

/**
 * Validate that a string is a valid hex color code.
 *
 * @param color - Color string to validate
 * @returns true if valid hex color (e.g., "#DC2626")
 */
export function isValidHexColor(color: string): boolean {
  return /^#[0-9A-Fa-f]{6}$/.test(color);
}

/**
 * Default color used when no color is specified.
 */
export const DEFAULT_TAG_COLOR = '#6B7280';

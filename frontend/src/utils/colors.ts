/**
 * TerraFlare Orbital Analytics Color System
 * Zero-glare dark-room mission operations palette with calibrated radiometric contrast.
 */

export const THEME_COLORS = {
  // Substrate & Canvas
  canvas: '#0B0F19',
  surface: '#0F131D',
  surfaceContainerLow: '#171B26',
  surfaceContainer: '#1C1F2A',
  surfaceContainerHigh: '#262A35',
  surfaceContainerHighest: '#313540',

  // Outlines & Borders
  border: '#1F2937',
  borderHighlight: '#374151',
  outline: '#A08E7A',

  // Primary Telemetry (Flame Amber & Solar Gold)
  primary: '#FFC174',
  primaryContainer: '#F59E0B',
  onPrimary: '#0B0F19',

  // Secondary Orbit & Grid (Orbital Cyan)
  secondary: '#7BD0FF',
  secondaryContainer: '#00A6E0',
  secondaryFixed: '#C4E7FF',

  // Sensor Provenance Channels
  modis: '#C084FC', // MODIS 1km Nadir Stream (Purple)
  modisBg: 'rgba(168, 85, 247, 0.15)',
  modisBorder: '#A855F7',

  viirs: '#FB923C', // VIIRS 375m I-Band Stream (Orange)
  viirsBg: 'rgba(249, 115, 22, 0.15)',
  viirsBorder: '#F97316',

  harmonized: '#FFC174', // Harmonized Unified Scale (Gold)
  harmonizedBg: 'rgba(255, 193, 116, 0.15)',
  harmonizedBorder: '#FFB95F',

  // Status & Telemetry Indicators
  success: '#10B981', // Sensor Emerald (Pipeline nominal)
  warning: '#F59E0B', // Alert Amber
  danger: '#EF4444', // Thermal Vermilion (Critical fire intensity)
  info: '#38BDF8', // Cyan telemetry

  // Neutral Foregrounds
  textPrimary: '#DFE2F1',
  textSecondary: '#D8C3AD',
  textMuted: '#9CA3AF',
  textDisabled: '#4B5563',
} as const;

export function getConfidenceColor(level: 'low' | 'nominal' | 'high' | 'unknown'): string {
  switch (level) {
    case 'high':
      return THEME_COLORS.success;
    case 'nominal':
      return THEME_COLORS.primary;
    case 'low':
      return THEME_COLORS.danger;
    default:
      return THEME_COLORS.textMuted;
  }
}


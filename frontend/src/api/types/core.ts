export interface HealthData {
  status: string;
  data_mode: 'fixture' | 'real';
  data_version: string;
  is_synthetic: boolean;
  features_enabled: string[];
}

export interface CapabilitiesData {
  sensors: string[];
  optional_fields: {
    frp: boolean;
    confidence: boolean;
    day_night: boolean;
    platform: boolean;
  };
  features_enabled: string[];
  h3_resolution: number;
}

export interface Region {
  region_id: string;
  name: string;
  bbox: [number, number, number, number];
}

export interface RegionsData {
  regions: Region[];
}

export interface HotspotFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    obs_id: string;
    sensor_family: 'MODIS' | 'VIIRS';
    platform?: string;
    acq_datetime_utc: string;
    confidence_class: 'low' | 'nominal' | 'high' | 'unknown';
    frp_mw: number | null;
  };
}

export interface HotspotsGeoJSON {
  type: 'FeatureCollection';
  truncated: boolean;
  features: HotspotFeature[];
}

export interface CellActivity {
  h3_cell: string;
  harmonized_value: number;
  lower: number;
  upper: number;
  modis_observed: number;
  viirs_observed: number;
}

export interface HotspotCellsData {
  h3_resolution: number;
  cells: CellActivity[];
}

export interface CalendarDay {
  date: string;
  harmonized_value: number;
  lower: number;
  upper: number;
  data_flag:
    | 'normal'
    | 'no_detections_recorded'
    | 'low_coverage_proxy';
}

export interface CalendarData {
  year: number;
  unit: string;
  days: CalendarDay[];
}

export interface HistoryYear {
  year: number;
  harmonized_value: number;
  lower: number;
  upper: number;
  modis_observed: number;
  viirs_observed: number;
  sensor_mix: string[];
}

export interface HistoryYearlyData {
  years: HistoryYear[];
}

export interface HistoryMonthCell {
  year: number;
  month: number;
  harmonized_value: number;
  lower: number;
  upper: number;
  is_partial: boolean;
}

export interface HistoryMonthlyData {
  matrix: HistoryMonthCell[];
}

export interface CurrentVsMedianData {
  year: number;
  month: number;
  is_partial: boolean;
  current: number;
  median: number;
  q25: number;
  q75: number;
  n_baseline_years: number;
  ratio_to_median: number | null;
}

export interface ComparisonPoint {
  period: string;
  modis_observed: number | null;
  viirs_observed: number | null;
  harmonized_value: number | null;
  lower: number | null;
  upper: number | null;
  is_provisional?: boolean | null;
}

export interface ComparisonProvenance {
  data_source: string;
  data_mode: string;
  is_synthetic: boolean;
  observation_count: number;
  date_range: { start: string | null; end: string | null };
  covered_days: number;
  synthetic_rows_detected?: number | null;
  viirs_platforms?: string[];
  reliability_status: string;
  processing_mode?: string | null;
  coverage_basis?: string | null;
  viirs_covered_days?: number | null;
  modis_covered_days?: number | null;
  value_types?: string[];
}

export interface ComparisonData {
  granularity: 'day' | 'week' | 'month';
  series: ComparisonPoint[];
  diagnostics: {
    correlation: number | null;
    co_detection_rate: number | null;
    overlap_period: { start: string | null; end: string | null };
    correlation_n?: number | null;
    co_detection_n?: number | null;
    correlation_deseasonalized?: number | null;
  };
  provenance?: ComparisonProvenance | null;
}

export interface CoverageYear {
  year: number;
  days_in_table: number;
  viirs_covered: number;
  modis_covered: number;
  both_covered: number;
  viirs_suspect_zero: number;
  modis_suspect_zero: number;
}

export interface CoverageGap { start: string; end: string; days: number }

export interface CoverageData {
  years: CoverageYear[];
  gaps: { viirs?: CoverageGap[]; modis?: CoverageGap[] };
  suspect_zero_days: { viirs?: string[]; modis?: string[] };
  basis?: string;
  assumption?: string;
  source?: string;
  date_range?: { start: string; end: string };
}

export interface FrpModel {
  platform: string;
  reference: string;
  status: string;
  frp_ratio: number | null;
  n_paired_cell_days: number | null;
  n_paired_days: number | null;
  temporal_rel_mae_monthly: number | null;
  spatial_rel_mae_monthly: number | null;
  temporal_bias_monthly: number | null;
}

export interface FrpCalibrationData {
  models: FrpModel[];
  source: string;
  reference?: string;
}

export interface MethodValidationMetric {
  metric: string;
  value: number | null;
  baseline: string;
}

export interface HarmonizationMethodData {
  method_id: string;
  description: string;
  overlap_period: {
    start: string;
    end: string;
  };
  assumptions: string[];
  limitations: string[];
  validation: MethodValidationMetric[];
}
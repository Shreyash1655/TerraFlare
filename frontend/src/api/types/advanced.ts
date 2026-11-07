
export interface SeasonYearStat {
  year: number;
  onset: string;
  peak: string;
  end: string;
  length_days: number;
  onset_doy?: number;
  peak_doy?: number;
  end_doy?: number;
  total_activity?: number;
  sensor_mix: string[];
  is_partial?: boolean;
  status?: string;
}

export interface SeasonShiftData {
  years: SeasonYearStat[];

  comparison: {
    baseline: [number, number];
    recent: [number, number];

    n_baseline_years?: number;
    n_recent_years?: number;

    onset_shift_days: {
      estimate: number | null;
      ci: [number | null, number | null];
    };

    end_shift_days: {
      estimate: number | null;
      ci: [number | null, number | null];
    };

    peak_shift_days?: {
      estimate: number | null;
      ci: [number | null, number | null];
    };

    peak_month_change: number | null;

    evidence:
      | 'strong_evidence'
      | 'moderate_evidence'
      | 'insufficient_evidence';
  };

  trend?: {
    n_years: number;
    onset_slope_days_per_year: number | null;
    onset_p_value: number | null;
    end_slope_days_per_year: number | null;
    end_p_value: number | null;
  };

  parameters?: {
    smooth_days: number;
    onset_pct: number;
    end_pct: number;
    ci_level: number;
    bootstrap_n: number;
  };

  notes?: string[];
}

// --------------------------------------------------
// FIRE MEMORY
// --------------------------------------------------

export interface FireMemoryCell {
  h3_cell: string;
  recurrence: number;
  years_active: number;
  years_in_range: number;
  trend_slope: number | null;
  memory_class:
    | 'persistent'
    | 'emerging'
    | 'declining'
    | 'sporadic';
}

export interface FireMemoryCellsData {
  cells: FireMemoryCell[];
}

export interface FireMemoryTimelineData {
  h3_cell: string;
  annual: Array<{
    year: number;
    harmonized_value: number;
    lower: number | null;
    upper: number | null;
  }>;
}

// --------------------------------------------------
// ANOMALIES
// --------------------------------------------------

export interface AnomalyPeriod {
  period_start: string;
  period_end: string;
  observed: number;
  baseline_median: number;
  robust_z: number | null;
  percentile: number | null;
  n_baseline_years: number;
}

export interface AnomaliesData {
  periods: AnomalyPeriod[];
}

export interface AnomalyExplainData {
  period: {
    start: string;
    end: string;
  };

  score: {
    robust_z: number | null;
    percentile: number | null;
  };

  top_dates: Array<{
    date: string;
    excess: number;
    share: number;
  }>;

  top_cells: Array<{
    h3_cell: string;
    excess: number;
    share: number;
  }>;

  explanation: string;
}

// --------------------------------------------------
// EVENTS
// --------------------------------------------------

export interface EventEpisode {
  event_id: string;
  first_detection: string;
  last_detection: string;
  n_detections: number;
  sensors: string[];
  centroid: [number, number];
  footprint_geojson: Record<string, unknown> | null;
}

export interface EventsData {
  events: EventEpisode[];
  label: string;
}

export interface EventDetailData {
  event_id: string;

  daily: Array<{
    date: string;
    n_detections: number;
    frp_sum_mw: number | null;
    frp_max_mw: number | null;
  }>;

  parameters: {
    eps_km: number;
    time_scale_km_per_day: number;
    min_samples: number;
  };
}

// --------------------------------------------------
// EXPOSURE
// --------------------------------------------------

export interface ExposureLayerResult {
  layer_id: string;
  source: string;
  version: string;
  count: number | null;
  sum_value: number | null;
  available: boolean;
}

export interface ExposureData {
  buffer_km: number;
  layers: ExposureLayerResult[];
  note: string;
}

// --------------------------------------------------
// QUALITY
// --------------------------------------------------

export interface QualityData {
  sensor_contribution: Array<{
    period: string;
    sensor_family: string;
    share: number;
  }>;

  confidence_distribution: Array<{
    sensor_family: string;
    native_class: string;
    count: number;
  }>;

  availability: Array<{
    sensor_family: string;
    gap_start: string;
    gap_end: string;
    label: string;
  }>;

  uncertainty_summary: {
    interval_level: number | null;
  };
}

// --------------------------------------------------
// PROVENANCE
// --------------------------------------------------

export interface ProvenanceRecord {
  source_id: string;
  product_version: string;
  file_name: string;
  sha256: string;
  rows_in: number;
  ingested_at: string;
}

export interface ProvenanceData {
  sources: ProvenanceRecord[];
}

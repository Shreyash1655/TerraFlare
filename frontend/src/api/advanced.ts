import { request } from './client';
import type { ApiResponse } from './types/common';
import type {
  SeasonShiftData,
  FireMemoryCellsData,
  FireMemoryTimelineData,
  AnomaliesData,
  AnomalyExplainData,
  EventsData,
  EventDetailData,
  ExposureData,
  QualityData,
  ProvenanceData,
} from './types/advanced';

export type FireMemoryClass =
  | 'persistent'
  | 'emerging'
  | 'declining'
  | 'sporadic';

// --------------------------------------------------
// SEASON SHIFT
// --------------------------------------------------

export async function getSeasonShift(params?: {
  region_id?: string;
  baseline_start?: number;
  baseline_end?: number;
  recent_start?: number;
  recent_end?: number;
}): Promise<ApiResponse<SeasonShiftData>> {
  return request<SeasonShiftData>(
    {
      url: '/advanced/season-shift',
      method: 'GET',
      params,
    },
    () => ({
      years: [
        { year: 2020, onset: '2020-06-12', peak: '2020-08-14', end: '2020-10-04', length_days: 114, sensor_mix: ['MODIS', 'VIIRS'] },
        { year: 2021, onset: '2021-06-08', peak: '2021-08-11', end: '2021-10-09', length_days: 123, sensor_mix: ['MODIS', 'VIIRS'] },
        { year: 2022, onset: '2022-06-15', peak: '2022-08-16', end: '2022-10-02', length_days: 109, sensor_mix: ['MODIS', 'VIIRS'] },
        { year: 2023, onset: '2023-05-30', peak: '2023-08-08', end: '2023-10-12', length_days: 135, sensor_mix: ['MODIS', 'VIIRS'] },
        { year: 2024, onset: '2024-05-24', peak: '2024-08-09', end: '2024-10-14', length_days: 143, sensor_mix: ['MODIS', 'VIIRS'] },
        { year: 2025, onset: '2025-05-28', peak: '2025-08-10', end: '2025-10-11', length_days: 136, sensor_mix: ['MODIS', 'VIIRS'] },
      ],
      comparison: {
        baseline: [2002, 2012],
        recent: [2015, 2025],
        onset_shift_days: { estimate: -18.4, ci: [-24.1, -11.8] },
        end_shift_days: { estimate: 11.2, ci: [4.2, 17.6] },
        peak_month_change: -13.0,
        evidence: 'strong_evidence',
      },
    })
  );
}

// --------------------------------------------------
// FIRE MEMORY
// --------------------------------------------------

export async function getFireMemoryCells(params?: {
  region_id?: string;
  class?: FireMemoryClass;
}): Promise<ApiResponse<FireMemoryCellsData>> {
  return request<FireMemoryCellsData>(
    {
      url: '/advanced/fire-memory/cells',
      method: 'GET',
      params,
    },
    () => ({
      cells: [
        { h3_cell: '872830828ffffff', recurrence: 0.85, years_active: 17, years_in_range: 20, trend_slope: 0.12, memory_class: 'persistent' },
        { h3_cell: '872830829ffffff', recurrence: 0.45, years_active: 9, years_in_range: 20, trend_slope: 0.44, memory_class: 'emerging' },
        { h3_cell: '87283082affffff', recurrence: 0.50, years_active: 10, years_in_range: 20, trend_slope: -0.32, memory_class: 'declining' },
        { h3_cell: '87283082bffffff', recurrence: 0.20, years_active: 4, years_in_range: 20, trend_slope: 0.01, memory_class: 'sporadic' },
      ],
    })
  );
}

export async function getFireMemoryTimeline(
  h3_cell: string
): Promise<ApiResponse<FireMemoryTimelineData>> {
  return request<FireMemoryTimelineData>(
    {
      url: `/advanced/fire-memory/cells/${encodeURIComponent(h3_cell)}/timeline`,
      method: 'GET',
    },
    () => ({
      h3_cell,
      annual: [
        { year: 2020, harmonized_value: 240, lower: 220, upper: 260 },
        { year: 2021, harmonized_value: 310, lower: 285, upper: 335 },
        { year: 2022, harmonized_value: 195, lower: 180, upper: 210 },
        { year: 2023, harmonized_value: 412, lower: 380, upper: 440 },
        { year: 2024, harmonized_value: 395, lower: 370, upper: 420 },
        { year: 2025, harmonized_value: 310, lower: 294, upper: 328 },
      ],
    })
  );
}

// --------------------------------------------------
// ANOMALIES
// --------------------------------------------------

export async function getAnomalies(params?: {
  region_id?: string;
  start?: string;
  end?: string;
}): Promise<ApiResponse<AnomaliesData>> {
  return request<AnomaliesData>(
    {
      url: '/advanced/anomalies',
      method: 'GET',
      params,
    },
    () => ({
      periods: [
        { period_start: '2024-08-05', period_end: '2024-08-11', observed: 2420, baseline_median: 1100, robust_z: 2.14, percentile: 94.2, n_baseline_years: 23 },
        { period_start: '2024-08-12', period_end: '2024-08-18', observed: 4890, baseline_median: 1270, robust_z: 3.84, percentile: 99.4, n_baseline_years: 23 },
        { period_start: '2024-08-19', period_end: '2024-08-25', observed: 3150, baseline_median: 1180, robust_z: 2.62, percentile: 96.8, n_baseline_years: 23 },
      ],
    })
  );
}

export async function getAnomalyExplain(params?: {
  region_id?: string;
  period_start?: string;
}): Promise<ApiResponse<AnomalyExplainData>> {
  return request<AnomalyExplainData>(
    {
      url: '/advanced/anomalies/explain',
      method: 'GET',
      params,
    },
    () => ({
      period: { start: '2024-08-12', end: '2024-08-18' },
      score: { robust_z: 3.84, percentile: 99.4 },
      top_dates: [
        { date: '2024-08-17', excess: 1420, share: 0.39 },
        { date: '2024-08-16', excess: 1180, share: 0.32 },
        { date: '2024-08-18', excess: 780, share: 0.21 },
      ],
      top_cells: [
        { h3_cell: '872830828ffffff', excess: 640, share: 0.18 },
        { h3_cell: '872830829ffffff', excess: 510, share: 0.14 },
      ],
      explanation:
        'Thermal radiance in target period 2024-W33 reached 3.84 standard robust deviations above the 2000–2023 climatological median. Detections concentrated on August 16–18 in 14 spatial cells explaining 74.2% of the anomaly.',
    })
  );
}

// --------------------------------------------------
// EVENTS
// --------------------------------------------------

export async function getEvents(params?: {
  region_id?: string;
  start?: string;
  end?: string;
}): Promise<ApiResponse<EventsData>> {
  return request<EventsData>(
    {
      url: '/advanced/events',
      method: 'GET',
      params,
    },
    () => ({
      label: 'Spatiotemporally grouped hotspot activity episodes (DBSCAN), not confirmed wildfires',
      events: [
        {
          event_id: 'EP-2024-PACNW-042',
          first_detection: '2024-08-14T18:22:00Z',
          last_detection: '2024-08-28T04:15:00Z',
          n_detections: 1420,
          sensors: ['VIIRS', 'MODIS'],
          centroid: [44.12, -121.85],
          footprint_geojson: null,
        },
        {
          event_id: 'EP-2024-PACNW-043',
          first_detection: '2024-08-16T12:05:00Z',
          last_detection: '2024-08-22T21:40:00Z',
          n_detections: 480,
          sensors: ['VIIRS'],
          centroid: [44.38, -121.52],
          footprint_geojson: null,
        },
      ],
    })
  );
}

export async function getEventDetail(
  event_id: string
): Promise<ApiResponse<EventDetailData>> {
  return request<EventDetailData>(
    {
      url: `/advanced/events/${encodeURIComponent(event_id)}`,
      method: 'GET',
    },
    () => ({
      event_id,
      daily: [
        { date: '2024-08-15', n_detections: 120, frp_sum_mw: 840, frp_max_mw: 210 },
        { date: '2024-08-16', n_detections: 340, frp_sum_mw: 2450, frp_max_mw: 412 },
        { date: '2024-08-17', n_detections: 512, frp_sum_mw: 4192, frp_max_mw: 540 },
        { date: '2024-08-18', n_detections: 448, frp_sum_mw: 3620, frp_max_mw: 380 },
      ],
      parameters: {
        eps_km: 1.5,
        time_scale_km_per_day: 1.0,
        min_samples: 8,
      },
    })
  );
}

// --------------------------------------------------
// EXPOSURE
// --------------------------------------------------

export async function getExposure(params?: {
  region_id?: string;
  buffer_km?: number;
}): Promise<ApiResponse<ExposureData>> {
  const buffer = params?.buffer_km ?? 5;

  return request<ExposureData>(
    {
      url: '/advanced/exposure',
      method: 'GET',
      params,
    },
    () => ({
      buffer_km: buffer,
      note: 'Proximity index only. This denotes mapped assets within buffer radius of detections, not confirmed fire damage or casualty risk.',
      layers: [
        { layer_id: 'settlements_osm', source: 'OpenStreetMap Extracts', version: '2026.1', count: 4, sum_value: null, available: true },
        { layer_id: 'population_ghsl', source: 'Global Human Settlement Layer', version: 'GHS-POP-2023', count: null, sum_value: 3840, available: true },
        { layer_id: 'transport_corridors', source: 'OSM Highways Primary/Secondary', version: '2026.1', count: 42, sum_value: 68.4, available: true },
        { layer_id: 'protected_areas_wdpa', source: 'World Database on Protected Areas', version: 'WDPA-2025', count: 2, sum_value: 124.0, available: true },
      ],
    })
  );
}

// --------------------------------------------------
// QUALITY
// --------------------------------------------------

export async function getQuality(): Promise<ApiResponse<QualityData>> {
  return request<QualityData>(
    {
      url: '/advanced/quality',
      method: 'GET',
    },
    () => ({
      sensor_contribution: [
        { period: '2024-08', sensor_family: 'VIIRS', share: 0.71 },
        { period: '2024-08', sensor_family: 'MODIS', share: 0.29 },
      ],
      confidence_distribution: [
        { sensor_family: 'VIIRS', native_class: 'high (>80%)', count: 81020 },
        { sensor_family: 'VIIRS', native_class: 'nominal (50-80%)', count: 31745 },
        { sensor_family: 'VIIRS', native_class: 'low (<50%)', count: 5685 },
        { sensor_family: 'MODIS', native_class: 'high (>80%)', count: 32400 },
        { sensor_family: 'MODIS', native_class: 'nominal (30-80%)', count: 13117 },
        { sensor_family: 'MODIS', native_class: 'low (<30%)', count: 2803 },
      ],
      availability: [
        {
          sensor_family: 'MODIS',
          gap_start: '2024-04-12',
          gap_end: '2024-04-14',
          label: 'no detections recorded (possible heavy overcast or orbital maneuver)',
        },
      ],
      uncertainty_summary: {
        interval_level: 95,
      },
    })
  );
}

// --------------------------------------------------
// PROVENANCE
// --------------------------------------------------

export async function getProvenance(): Promise<ApiResponse<ProvenanceData>> {
  return request<ProvenanceData>(
    {
      url: '/advanced/quality/provenance',
      method: 'GET',
    },
    () => ({
      sources: [
        {
          source_id: 'nasa_firms_viirs_snpp',
          product_version: 'VNP14IMG-NRT',
          file_name: 'VIIRS_SNPP_NRT_PacNW_2024.csv',
          sha256: '4c8ea7b039f1c42f',
          rows_in: 118450,
          ingested_at: '2026-03-31T20:14:00Z',
        },
        {
          source_id: 'nasa_firms_modis_aqua_terra',
          product_version: 'MCD14DL-C6.1',
          file_name: 'MODIS_C6_1_PacNW_2024.csv',
          sha256: '9a12e3448e20f17b',
          rows_in: 48320,
          ingested_at: '2026-03-31T20:18:00Z',
        },
        {
          source_id: 'terraflare_h3_harmonized_mesh',
          product_version: 'v2026.11.13-r1',
          file_name: 'h3_cell_day_canonical_v1.parquet',
          sha256: '7e9a3bc418a092ef',
          rows_in: 142890,
          ingested_at: '2026-03-31T20:25:00Z',
        },
      ],
    })
  );
}
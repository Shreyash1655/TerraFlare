
import { apiClient, API_MODE, request } from './client';
import type { ApiResponse, ApiMeta } from './types/common';

import type {
  HealthData,
  CapabilitiesData,
  RegionsData,
  HotspotsGeoJSON,
  HotspotCellsData,
  CalendarData,
  HistoryYearlyData,
  HistoryMonthlyData,
  CurrentVsMedianData,
  ComparisonData,
  HarmonizationMethodData,
} from './types/core';

// --------------------------------------------------
// HEALTH
// --------------------------------------------------

export async function getHealth(): Promise<ApiResponse<HealthData>> {
  if (API_MODE === 'mock') {
    return request<HealthData>(
      { url: '/advanced/health', method: 'GET' },
      () => ({
        status: 'ok',
        data_mode: 'fixture',
        data_version: 'frontend-mock',
        is_synthetic: true,
        features_enabled: [
          'season-shift',
          'fire-memory',
          'anomaly',
          'events',
          'exposure',
          'quality',
        ],
      })
    );
  }

  const response = await apiClient.get<HealthData>('/advanced/health');
  const health = response.data;

  const meta: ApiMeta = {
    api_version: 'v1',
    data_version: health.data_version,
    data_mode: health.data_mode,
    is_synthetic: health.is_synthetic,
    method_id: 'health-check',
    generated_at: new Date().toISOString(),
    parameters: {},
    limitations: [],
  };

  return {
    meta,
    data: health,
  };
}

// --------------------------------------------------
// CAPABILITIES
// --------------------------------------------------

export async function getCapabilities(): Promise<ApiResponse<CapabilitiesData>> {
  return request<CapabilitiesData>(
    { url: '/meta/capabilities', method: 'GET' },
    () => ({
      sensors: ['MODIS', 'VIIRS'],
      optional_fields: {
        frp: true,
        confidence: true,
        day_night: true,
        platform: true,
      },
      features_enabled: [
        'season-shift',
        'anomaly',
        'quality',
        'fire-memory',
      ],
      h3_resolution: 7,
    })
  );
}

// --------------------------------------------------
// REGIONS
// --------------------------------------------------

export async function getRegions(): Promise<ApiResponse<RegionsData>> {
  return request<RegionsData>(
    { url: '/regions', method: 'GET' },
    () => ({
      regions: [
        {
          region_id: 'pwn',
          name: 'Western North America - Pacific NW',
          bbox: [-125.0, 42.0, -116.0, 49.0],
        },
        {
          region_id: 'amz',
          name: 'Amazon Basin Tropical Arc',
          bbox: [-70.0, -15.0, -50.0, -2.0],
        },
        {
          region_id: 'sib',
          name: 'Siberian Boreal Zone',
          bbox: [90.0, 55.0, 125.0, 70.0],
        },
        {
          region_id: 'aus',
          name: 'SE Australia Eurobodalla',
          bbox: [148.0, -38.0, 151.0, -34.0],
        },
      ],
    })
  );
}

// --------------------------------------------------
// HOTSPOTS
// --------------------------------------------------

export async function getHotspots(params?: {
  region_id?: string;
  start?: string;
  end?: string;
  sensors?: string;
  min_confidence?: string;
  limit?: number;
}): Promise<ApiResponse<HotspotsGeoJSON>> {
  return request<HotspotsGeoJSON>(
    { url: '/hotspots', method: 'GET', params },
    () => ({
      type: 'FeatureCollection',
      truncated: false,
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [-121.85, 44.12],
          },
          properties: {
            obs_id: 'viirs-20240818-001',
            sensor_family: 'VIIRS',
            platform: 'NOAA-20',
            acq_datetime_utc: '2024-08-18T20:45:00Z',
            confidence_class: 'high',
            frp_mw: 142.4,
          },
        },
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [-121.82, 44.10],
          },
          properties: {
            obs_id: 'modis-20240818-002',
            sensor_family: 'MODIS',
            platform: 'Aqua',
            acq_datetime_utc: '2024-08-18T21:15:00Z',
            confidence_class: 'nominal',
            frp_mw: 98.2,
          },
        },
      ],
    })
  );
}

// --------------------------------------------------
// HOTSPOT CELLS
// --------------------------------------------------

export async function getHotspotCells(params?: {
  region_id?: string;
  start?: string;
  end?: string;
  h3_res?: number;
}): Promise<ApiResponse<HotspotCellsData>> {
  return request<HotspotCellsData>(
    { url: '/hotspots/cells', method: 'GET', params },
    () => ({
      h3_resolution: params?.h3_res ?? 7,
      cells: [
        {
          h3_cell: '872830828ffffff',
          harmonized_value: 310.4,
          lower: 294.1,
          upper: 328.0,
          modis_observed: 242,
          viirs_observed: 600,
        },
      ],
    })
  );
}

// --------------------------------------------------
// CALENDAR
// --------------------------------------------------

export async function getCalendar(params?: {
  region_id?: string;
  year?: number;
}): Promise<ApiResponse<CalendarData>> {
  const year = params?.year ?? 2026;

  return request<CalendarData>(
    { url: '/calendar', method: 'GET', params },
    () => ({
      year,
      unit: 'harmonized activity index',
      days: Array.from({ length: 30 }, (_, i) => ({
        date: `${year}-08-${String(i + 1).padStart(2, '0')}`,
        harmonized_value: 150 + ((i * 37) % 151),
        lower: 140,
        upper: 480,
        data_flag: 'normal',
      })),
    })
  );
}

// --------------------------------------------------
// YEARLY HISTORY
// --------------------------------------------------

export async function getHistoryYearly(params?: {
  region_id?: string;
}): Promise<ApiResponse<HistoryYearlyData>> {
  return request<HistoryYearlyData>(
    { url: '/history/yearly', method: 'GET', params },
    () => ({
      years: [
        {
          year: 2020,
          harmonized_value: 128400,
          lower: 122000,
          upper: 135000,
          modis_observed: 44000,
          viirs_observed: 104000,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
        {
          year: 2021,
          harmonized_value: 139200,
          lower: 133000,
          upper: 146000,
          modis_observed: 46200,
          viirs_observed: 112000,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
        {
          year: 2022,
          harmonized_value: 124500,
          lower: 118000,
          upper: 131000,
          modis_observed: 41800,
          viirs_observed: 99400,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
        {
          year: 2023,
          harmonized_value: 148900,
          lower: 141000,
          upper: 156000,
          modis_observed: 49500,
          viirs_observed: 121000,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
        {
          year: 2024,
          harmonized_value: 154200,
          lower: 146000,
          upper: 162000,
          modis_observed: 51200,
          viirs_observed: 128400,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
        {
          year: 2025,
          harmonized_value: 142890,
          lower: 138770,
          upper: 147010,
          modis_observed: 48320,
          viirs_observed: 118450,
          sensor_mix: ['MODIS', 'VIIRS'],
        },
      ],
    })
  );
}

// --------------------------------------------------
// MONTHLY HISTORY
// --------------------------------------------------

export async function getHistoryMonthly(params?: {
  region_id?: string;
}): Promise<ApiResponse<HistoryMonthlyData>> {
  return request<HistoryMonthlyData>(
    { url: '/history/monthly', method: 'GET', params },
    () => ({
      matrix: [
        {
          year: 2024,
          month: 8,
          harmonized_value: 48200,
          lower: 45000,
          upper: 51000,
          is_partial: false,
        },
        {
          year: 2024,
          month: 9,
          harmonized_value: 29400,
          lower: 27000,
          upper: 31500,
          is_partial: false,
        },
      ],
    })
  );
}

// --------------------------------------------------
// CURRENT VS MEDIAN
// --------------------------------------------------

export async function getCurrentVsMedian(params?: {
  region_id?: string;
  month?: number;
}): Promise<ApiResponse<CurrentVsMedianData>> {
  return request<CurrentVsMedianData>(
    { url: '/history/current-vs-median', method: 'GET', params },
    () => ({
      year: 2026,
      month: params?.month ?? 8,
      is_partial: false,
      current: 512,
      median: 342,
      q25: 240,
      q75: 480,
      n_baseline_years: 24,
      ratio_to_median: 1.497,
    })
  );
}

// --------------------------------------------------
// HARMONIZATION COMPARISON
// --------------------------------------------------

export async function getHarmonizationComparison(params?: {
  region_id?: string;
  granularity?: 'day' | 'week' | 'month';
}): Promise<ApiResponse<ComparisonData>> {
  return request<ComparisonData>(
    { url: '/harmonization/comparison', method: 'GET', params },
    () => ({
      granularity: params?.granularity ?? 'week',
      series: [
        {
          period: '2024-W30',
          modis_observed: 420,
          viirs_observed: 1040,
          harmonized_value: 890,
          lower: 840,
          upper: 940,
        },
        {
          period: '2024-W31',
          modis_observed: 680,
          viirs_observed: 1680,
          harmonized_value: 1420,
          lower: 1350,
          upper: 1490,
        },
        {
          period: '2024-W32',
          modis_observed: 1120,
          viirs_observed: 2840,
          harmonized_value: 2380,
          lower: 2260,
          upper: 2500,
        },
        {
          period: '2024-W33',
          modis_observed: 1840,
          viirs_observed: 4620,
          harmonized_value: 3910,
          lower: 3710,
          upper: 4110,
        },
      ],
      diagnostics: {
        correlation: 0.89,
        co_detection_rate: 0.62,
        overlap_period: {
          start: '2012-01-01',
          end: '2025-12-31',
        },
      },
    })
  );
}

// --------------------------------------------------
// HARMONIZATION METHOD
// --------------------------------------------------

export async function getHarmonizationMethod(): Promise<
  ApiResponse<HarmonizationMethodData>
> {
  return request<HarmonizationMethodData>(
    { url: '/harmonization/method', method: 'GET' },
    () => ({
      method_id: 'M2-Stratified-Ratio',
      description:
        'Stratified biome by seasonal diurnal pass scaling transfer functions on H3 cell-day grains.',
      overlap_period: {
        start: '2012-01-01',
        end: '2025-12-31',
      },
      assumptions: [
        'Stationary fire behaviour between satellite overpass intervals',
        'Uniform cloud distribution between Aqua (13:30 LT) and S-NPP (13:30 LT) orbits',
      ],
      limitations: [
        'Off-nadir pixel expansion (bowtie effect) broadens uncertainty up to 1.8x at scan edge',
        'Sub-pixel smoldering fires may evade MODIS 1km sensor noise floor',
      ],
      validation: [
        {
          metric: 'Rel-MAE (%)',
          value: 18.2,
          baseline: 'M0 (48.2%)',
        },
        {
          metric: 'Rank-Corr (ρ)',
          value: 0.89,
          baseline: 'M0 (0.72)',
        },
        {
          metric: '95% Interval Coverage (%)',
          value: 94.6,
          baseline: 'M0 (61.4%)',
        },
      ],
    })
  );
}

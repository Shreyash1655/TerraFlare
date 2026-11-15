
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

// --------------------------------------------------
// FIRE MEMORY CLASS
// --------------------------------------------------

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
  return request<SeasonShiftData>({
    url: '/advanced/season-shift',
    method: 'GET',
    params,
  });
}

// --------------------------------------------------
// FIRE MEMORY
// --------------------------------------------------

export async function getFireMemoryCells(params?: {
  region_id?: string;
  class?: FireMemoryClass;
}): Promise<ApiResponse<FireMemoryCellsData>> {
  return request<FireMemoryCellsData>({
    url: '/advanced/fire-memory/cells',
    method: 'GET',
    params,
  });
}

export async function getFireMemoryTimeline(
  h3_cell: string
): Promise<ApiResponse<FireMemoryTimelineData>> {
  return request<FireMemoryTimelineData>({
    url: `/advanced/fire-memory/cells/${encodeURIComponent(h3_cell)}/timeline`,
    method: 'GET',
  });
}

// --------------------------------------------------
// ANOMALIES
// --------------------------------------------------

export async function getAnomalies(params?: {
  region_id?: string;
  start?: string;
  end?: string;
}): Promise<ApiResponse<AnomaliesData>> {
  return request<AnomaliesData>({
    url: '/advanced/anomalies',
    method: 'GET',
    params,
  });
}

export async function getAnomalyExplain(params: {
  region_id?: string;
  start: string;
  end: string;
}): Promise<ApiResponse<AnomalyExplainData>> {
  return request<AnomalyExplainData>({
    url: '/advanced/anomalies/explain',
    method: 'GET',
    params,
  });
}

// --------------------------------------------------
// EVENTS
// --------------------------------------------------

export interface ScopeParams {
  region_id?: string;
  start?: string;
  end?: string;
  bbox?: string;
  sensor?: 'viirs' | 'modis';
}

export async function getEvents(
  params?: ScopeParams
): Promise<ApiResponse<EventsData>> {
  return request<EventsData>({
    url: '/advanced/events',
    method: 'GET',
    params,
  });
}

export async function getEventDetail(
  event_id: string,
  params?: ScopeParams
): Promise<ApiResponse<EventDetailData>> {
  return request<EventDetailData>({
    url: `/advanced/events/${encodeURIComponent(event_id)}`,
    method: 'GET',
    params,
  });
}

export async function getExposure(
  params?: ScopeParams & { buffer_km?: number }
): Promise<ApiResponse<ExposureData>> {
  return request<ExposureData>({
    url: '/advanced/exposure',
    method: 'GET',
    params,
  });
}

// --------------------------------------------------
// QUALITY
// --------------------------------------------------

export async function getQuality(): Promise<ApiResponse<QualityData>> {
  return request<QualityData>({
    url: '/advanced/quality',
    method: 'GET',
  });
}

// --------------------------------------------------
// PROVENANCE
// --------------------------------------------------

export async function getProvenance(): Promise<ApiResponse<ProvenanceData>> {
  return request<ProvenanceData>({
    url: '/advanced/quality/provenance',
    method: 'GET',
  });
}
export interface HistoryModuleStatus {
  required_years: number;
  sufficient: boolean;
  message: string | null;
}
export interface HistoryStatusData {
  source: string;
  is_synthetic: boolean;
  available_days: number;
  span_days: number;
  date_range: [string | null, string | null];
  modules: Record<string, HistoryModuleStatus>;
}

export async function getHistoryStatus(): Promise<ApiResponse<HistoryStatusData>> {
  return request<HistoryStatusData>({ url: '/advanced/history-status', method: 'GET' });
}
export interface ShortWindowDay {
  date: string;
  count: number;
  robust_z: number | null;
  flagged: boolean;
}
export interface ShortWindowAnomalyData {
  method: string;
  sensor: string;
  window: [string, string];
  usable_days: number;
  min_days: number;
  warnings: string[];
  days: ShortWindowDay[];
}
export interface ShortWindowCell {
  h3_cell: string;
  days_active: number;
  days_covered: number;
  share: number | null;
  detections: number;
}
export interface ShortWindowPersistenceData {
  method: string;
  sensor: string;
  covered_days: number;
  min_days: number;
  warnings: string[];
  n_cells: number;
  cells_full: number;
  cells: ShortWindowCell[];
}

export async function getShortWindowAnomalies(
  sensor: 'viirs' | 'modis'
): Promise<ApiResponse<ShortWindowAnomalyData>> {
  return request<ShortWindowAnomalyData>({
    url: '/advanced/short-window/anomalies',
    method: 'GET',
    params: { sensor },
  });
}

export async function getShortWindowPersistence(
  sensor: 'viirs' | 'modis',
  limit = 100
): Promise<ApiResponse<ShortWindowPersistenceData>> {
  return request<ShortWindowPersistenceData>({
    url: '/advanced/short-window/persistence',
    method: 'GET',
    params: { sensor, limit },
  });
}
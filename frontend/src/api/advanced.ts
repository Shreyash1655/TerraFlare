
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

export async function getAnomalyExplain(params?: {
  region_id?: string;
  period_start?: string;
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

export async function getEvents(params?: {
  region_id?: string;
  start?: string;
  end?: string;
}): Promise<ApiResponse<EventsData>> {
  return request<EventsData>({
    url: '/advanced/events',
    method: 'GET',
    params,
  });
}

export async function getEventDetail(
  event_id: string
): Promise<ApiResponse<EventDetailData>> {
  return request<EventDetailData>({
    url: `/advanced/events/${encodeURIComponent(event_id)}`,
    method: 'GET',
  });
}

// --------------------------------------------------
// EXPOSURE
// --------------------------------------------------

export async function getExposure(params?: {
  region_id?: string;
  buffer_km?: number;
}): Promise<ApiResponse<ExposureData>> {
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

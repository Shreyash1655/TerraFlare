
import { useEffect, useMemo, useState } from 'react';
import { getEvents, getEventDetail } from '../../../api/advanced';
import type {
  EventsData,
  EventEpisode,
  EventDetailData,
} from '../../../api/types/advanced';

function formatDate(value: string | null | undefined) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  });
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
  });
}

function getDuration(first: string, last: string) {
  const start = new Date(first).getTime();
  const end = new Date(last).getTime();

  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return '—';
  }

  const days = (end - start) / (1000 * 60 * 60 * 24);

  return `${days.toFixed(1)} days`;
}

function formatCentroid(centroid: [number, number] | undefined) {
  if (!centroid || centroid.length < 2) return '—';

  const [longitude, latitude] = centroid;

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return '—';
  }

  return `${Math.abs(latitude).toFixed(3)}°${latitude >= 0 ? 'N' : 'S'}, ${Math.abs(longitude).toFixed(3)}°${longitude >= 0 ? 'E' : 'W'}`;
}

function formatSensors(sensors: string[] | undefined) {
  if (!sensors?.length) return 'Not available';

  return sensors.join(' • ');
}

export default function EventsPage() {
  const [events, setEvents] = useState<EventEpisode[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const [eventDetail, setEventDetail] = useState<EventDetailData | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [dataMode, setDataMode] = useState<'fixture' | 'real'>('fixture');
  const [isSynthetic, setIsSynthetic] = useState(false);

  // Fetch clustered activity episodes.
  useEffect(() => {
    let active = true;

    async function loadEvents() {
      try {
        setLoadingEvents(true);
        setError(null);

        const response = await getEvents();

        if (!active) return;

        const data: EventsData = response.data;

        setEvents(data.events ?? []);
        setDataMode(response.meta.data_mode);
        setIsSynthetic(response.meta.is_synthetic);

        setSelectedEventId((current) => {
          if (
            current &&
            data.events?.some((event) => event.event_id === current)
          ) {
            return current;
          }

          return data.events?.[0]?.event_id ?? null;
        });
      } catch (err) {
        if (!active) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load activity episodes.',
        );
      } finally {
        if (active) setLoadingEvents(false);
      }
    }

    loadEvents();

    return () => {
      active = false;
    };
  }, []);

  // Fetch details whenever the selected episode changes.
  useEffect(() => {
    if (!selectedEventId) {
      setEventDetail(null);
      return;
    }

    // Capture the non-null ID for use inside the async function.
    const eventId = selectedEventId;
    let active = true;

    async function loadEventDetail() {
      try {
        setLoadingDetail(true);
        setDetailError(null);
        setEventDetail(null);

        const response = await getEventDetail(eventId);

        if (!active) return;

        setEventDetail(response.data);
      } catch (err) {
        if (!active) return;

        setDetailError(
          err instanceof Error
            ? err.message
            : 'Unable to load episode details.',
        );
      } finally {
        if (active) setLoadingDetail(false);
      }
    }

    loadEventDetail();

    return () => {
      active = false;
    };
  }, [selectedEventId]);

  const selectedEvent = useMemo(
    () =>
      events.find((event) => event.event_id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const dailyStats = eventDetail?.daily ?? [];

  const totalDetections = dailyStats.reduce(
    (total, day) => total + (day.n_detections ?? 0),
    0,
  );

  const totalFrp = dailyStats.reduce(
    (total, day) => total + (day.frp_sum_mw ?? 0),
    0,
  );

  const maxFrp = dailyStats.reduce(
    (maximum, day) => Math.max(maximum, day.frp_max_mw ?? 0),
    0,
  );

  const firstDetection = selectedEvent?.first_detection;
  const lastDetection = selectedEvent?.last_detection;

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER C INTEL • SUBSYSTEM 07
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                SPATIOTEMPORAL DBSCAN CLUSTERING
              </span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Fire Event Intelligence &amp; Episode Tracking
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Groups nearby active-fire detections across space and time into
              activity episodes. Explore episode duration, detection counts,
              sensor information and daily fire radiative power measurements.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#a08e7a]">
              {eventDetail?.parameters
                ? `ε = ${eventDetail.parameters.eps_km} km • Min Samples = ${eventDetail.parameters.min_samples}`
                : 'DBSCAN PARAMETERS'}
            </span>
          </div>
        </div>

        {/* Data Mode */}
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <span className="px-2 py-1 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#7bd0ff]">
            DATA MODE: {dataMode.toUpperCase()}
          </span>

          {isSynthetic && (
            <span className="px-2 py-1 rounded bg-[#30251a] border border-[#70502b] text-xs font-caption-mono text-[#ffc174]">
              SYNTHETIC DATA — NOT OBSERVED FIRE ACTIVITY
            </span>
          )}
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-start gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">
            warning
          </span>
          <span>
            <strong className="text-[#dfe2f1]">
              SCIENTIFIC CONSTRAINTS:
            </strong>{' '}
            An activity episode represents a clustered collection of satellite
            detections, not a verified wildfire perimeter. The footprint bounds
            the observed sensor points, not the physical burned area.
          </span>
        </div>
      </section>

      <div className="w-full px-6 py-6 space-y-6">
        {/* Loading */}
        {loadingEvents && (
          <div className="p-8 text-center rounded-lg bg-[#1c1f2a] border border-[#262a35]">
            <p className="text-[#7bd0ff] font-caption-mono text-sm">
              Loading activity episodes...
            </p>
          </div>
        )}

        {/* Error */}
        {!loadingEvents && error && (
          <div className="p-5 rounded-lg bg-[#301b20] border border-[#75343d]">
            <p className="text-[#ffbcb7] font-semibold text-sm">
              Unable to load activity episodes
            </p>
            <p className="text-[#d8c3ad] text-xs mt-2">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-3 px-3 py-2 rounded bg-[#ffc174] text-[#0a0e18] text-xs font-bold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loadingEvents && !error && events.length === 0 && (
          <div className="p-8 text-center rounded-lg bg-[#1c1f2a] border border-[#262a35]">
            <span className="material-symbols-outlined text-3xl text-[#a08e7a]">
              satellite_alt
            </span>
            <p className="text-[#dfe2f1] font-semibold mt-2">
              No activity episodes found
            </p>
            <p className="text-[#a08e7a] text-xs mt-1">
              No clustered episodes are available for the current dataset.
            </p>
          </div>
        )}

        {/* Episodes List & Detail Frame */}
        {!loadingEvents && !error && events.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Episodes List */}
            <div className="lg:col-span-6 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                  Clustered Activity Episodes
                </h3>
                <span className="text-xs font-caption-mono text-[#7bd0ff]">
                  {events.length} EPISODES
                </span>
              </div>

              <div className="space-y-3">
                {events.map((event) => {
                  const isSelected = selectedEventId === event.event_id;

                  return (
                    <button
                      type="button"
                      key={event.event_id}
                      onClick={() => setSelectedEventId(event.event_id)}
                      className={`w-full text-left p-4 rounded border transition-all ${
                        isSelected
                          ? 'bg-[#262a35] border-[#ffc174] shadow-md ring-1 ring-[#ffc174]'
                          : 'bg-[#171b26] border-[#262a35] hover:bg-[#262a35]/60'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5 gap-2">
                        <span className="font-caption-mono text-[10px] text-[#7bd0ff] font-bold">
                          {event.event_id}
                        </span>

                        <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-[10px] font-bold">
                          {getDuration(
                            event.first_detection,
                            event.last_detection,
                          )}
                        </span>
                      </div>

                      <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-2">
                        Activity Episode {event.event_id}
                      </h4>

                      <div className="grid grid-cols-2 gap-2 bg-[#0a0e18] p-2 rounded font-caption-mono text-xs">
                        <div>
                          <span className="text-[#a08e7a] text-[10px] block">
                            TOTAL DETECTIONS
                          </span>
                          <span className="text-[#dfe2f1] font-bold">
                            {formatNumber(event.n_detections)} spots
                          </span>
                        </div>

                        <div>
                          <span className="text-[#a08e7a] text-[10px] block">
                            SATELLITE SENSORS
                          </span>
                          <span className="text-[#dfe2f1] font-bold">
                            {event.sensors?.length ?? 0} sensors
                          </span>
                        </div>
                      </div>

                      <div className="mt-2 text-[11px] font-caption-mono text-[#a08e7a]">
                        Sensors:{' '}
                        <span className="text-[#dfe2f1]">
                          {formatSensors(event.sensors)}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Episode Inspector */}
            <div className="lg:col-span-6 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col">
              {!selectedEvent ? (
                <p className="text-[#a08e7a] text-sm">
                  Select an activity episode to inspect its details.
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4 gap-3">
                    <div>
                      <span className="font-caption-mono text-xs text-[#ffc174] font-bold">
                        EPISODE INSPECTOR
                      </span>
                      <h4 className="font-title-sm text-base font-bold text-[#dfe2f1] mt-0.5 break-all">
                        {selectedEvent.event_id}
                      </h4>
                    </div>

                    <span className="font-mono text-xs text-[#a08e7a] text-right">
                      {formatCentroid(selectedEvent.centroid)}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-4 font-caption-mono text-xs">
                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px]">
                        FIRST DETECTION (UTC)
                      </span>
                      <span className="text-[#dfe2f1] font-bold mt-0.5 block">
                        {formatDate(firstDetection)}
                      </span>
                    </div>

                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px]">
                        LAST DETECTION (UTC)
                      </span>
                      <span className="text-[#dfe2f1] font-bold mt-0.5 block">
                        {formatDate(lastDetection)}
                      </span>
                    </div>
                  </div>

                  {/* Episode Metrics */}
                  <div className="grid grid-cols-2 gap-3 mb-5">
                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px] font-caption-mono">
                        EPISODE DURATION
                      </span>
                      <span className="text-[#dfe2f1] font-bold text-lg">
                        {getDuration(
                          selectedEvent.first_detection,
                          selectedEvent.last_detection,
                        )}
                      </span>
                    </div>

                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px] font-caption-mono">
                        MAX DAILY FRP
                      </span>
                      <span className="text-[#ffbcb7] font-bold text-lg">
                        {loadingDetail ? '...' : `${formatNumber(maxFrp)} MW`}
                      </span>
                    </div>

                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px] font-caption-mono">
                        DAILY DETECTIONS TOTAL
                      </span>
                      <span className="text-[#dfe2f1] font-bold text-lg">
                        {loadingDetail ? '...' : formatNumber(totalDetections)}
                      </span>
                    </div>

                    <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                      <span className="text-[#a08e7a] block text-[10px] font-caption-mono">
                        SUM OF DAILY FRP
                      </span>
                      <span className="text-[#ffc174] font-bold text-lg">
                        {loadingDetail ? '...' : `${formatNumber(totalFrp)} MW`}
                      </span>
                    </div>
                  </div>

                  {/* Daily FRP Trajectory */}
                  <div className="flex items-center justify-between mb-2">
                    <h5 className="font-title-sm text-xs font-bold text-[#dfe2f1]">
                      Daily FRP Measurements
                    </h5>
                    <span className="font-caption-mono text-[10px] text-[#a08e7a]">
                      MW
                    </span>
                  </div>

                  {loadingDetail && (
                    <div className="p-5 text-center rounded bg-[#0a0e18]">
                      <p className="text-[#7bd0ff] text-xs font-caption-mono">
                        Loading episode telemetry...
                      </p>
                    </div>
                  )}

                  {!loadingDetail && detailError && (
                    <div className="p-3 rounded bg-[#301b20] border border-[#75343d]">
                      <p className="text-[#ffbcb7] text-xs">{detailError}</p>
                    </div>
                  )}

                  {!loadingDetail &&
                    !detailError &&
                    dailyStats.length === 0 && (
                      <div className="p-4 rounded bg-[#0a0e18] text-center">
                        <p className="text-[#a08e7a] text-xs">
                          No daily FRP measurements available for this episode.
                        </p>
                      </div>
                    )}

                  {!loadingDetail &&
                    !detailError &&
                    dailyStats.length > 0 && (
                      <div className="space-y-2 font-caption-mono text-xs max-h-64 overflow-y-auto pr-1">
                        {dailyStats.map((day) => {
                          const maximum = Math.max(maxFrp, 1);
                          const width = Math.min(
                            100,
                            ((day.frp_max_mw ?? 0) / maximum) * 100,
                          );

                          return (
                            <div
                              key={day.date}
                              className="p-2.5 rounded bg-[#0a0e18] border border-[#262a35]"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-bold text-[#dfe2f1]">
                                  {day.date}
                                </span>
                                <span className="text-[#a08e7a]">
                                  {formatNumber(day.n_detections)} detections
                                </span>
                                <span className="font-bold text-[#ffc174]">
                                  {formatNumber(day.frp_max_mw)} MW max
                                </span>
                              </div>

                              <div className="mt-2 h-1.5 rounded-full bg-[#262a35] overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-[#ffc174]"
                                  style={{ width: `${width}%` }}
                                />
                              </div>

                              <div className="mt-1 text-[10px] text-[#a08e7a]">
                                Daily FRP sum:{' '}
                                {formatNumber(day.frp_sum_mw)} MW
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                  {/* Footer */}
                  <div className="mt-6 pt-3 border-t border-[#262a35] flex flex-wrap justify-between gap-2 font-caption-mono text-xs text-[#a08e7a]">
                    <span>
                      Daily FRP sum:{' '}
                      <strong className="text-[#ffc174]">
                        {loadingDetail ? '...' : `${formatNumber(totalFrp)} MW`}
                      </strong>
                    </span>
                    <span>Footprint: Observed Detection Cluster</span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

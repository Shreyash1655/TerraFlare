
import { useEffect, useMemo, useState } from 'react';
import FilterBar from '../../../components/filters/FilterBar';
import {
  getRegions,
  getHotspots,
  getHotspotCells,
  getHistoryYearly,
  getHarmonizationComparison,
} from '../../../api/core';

type Region = {
  region_id: string;
  name: string;
};

type HotspotsResponse = Awaited<ReturnType<typeof getHotspots>>['data'];
type CellsResponse = Awaited<ReturnType<typeof getHotspotCells>>['data'];
type HistoryResponse = Awaited<ReturnType<typeof getHistoryYearly>>['data'];
type ComparisonResponse = Awaited<
  ReturnType<typeof getHarmonizationComparison>
>['data'];

type Overlay = 'hex' | 'raw' | 'frp';

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return Math.round(value).toLocaleString('en-IN');
}

function formatDecimal(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return value.toFixed(1);
}

function StatCard({
  label,
  value,
  unit,
  description,
  accent = 'text-[#ffc174]',
}: {
  label: string;
  value: string;
  unit?: string;
  description: string;
  accent?: string;
}) {
  return (
    <div className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col justify-between min-w-0">
      <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase tracking-wider">
        {label}
      </span>

      <div className="flex items-baseline gap-2 mt-2">
        <span className={`font-mono text-2xl font-bold tracking-tight ${accent}`}>
          {value}
        </span>

        {unit && (
          <span className="font-caption-mono text-xs text-[#a08e7a]">
            {unit}
          </span>
        )}
      </div>

      <p className="font-caption-mono text-[10px] text-[#d8c3ad] mt-2">
        {description}
      </p>
    </div>
  );
}

export default function DashboardPage() {
  const [activeOverlay, setActiveOverlay] = useState<Overlay>('hex');
  const [selectedHexRes, setSelectedHexRes] = useState(7);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);

  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState('');

  const [hotspots, setHotspots] = useState<HotspotsResponse | null>(null);
  const [cells, setCells] = useState<CellsResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [comparison, setComparison] =
    useState<ComparisonResponse | null>(null);

  const [dataMode, setDataMode] = useState<'fixture' | 'real' | null>(null);
  const [isSynthetic, setIsSynthetic] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load the configured regions.
  useEffect(() => {
    let active = true;

    async function loadRegions() {
      try {
        const response = await getRegions();

        if (!active) return;

        const availableRegions = response.data.regions ?? [];

        setRegions(availableRegions);

        if (availableRegions.length > 0) {
          setSelectedRegion(availableRegions[0].region_id);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : 'Unable to load regions.',
          );
          setLoading(false);
        }
      }
    }

    loadRegions();

    return () => {
      active = false;
    };
  }, []);

  // Fetch dashboard data when the region or H3 resolution changes.
  useEffect(() => {
    if (!selectedRegion) return;

    let active = true;

    async function loadDashboard() {
      setLoading(true);
      setError('');

      try {
        const [
          hotspotResponse,
          cellResponse,
          historyResponse,
          comparisonResponse,
        ] = await Promise.all([
          getHotspots({
            region_id: selectedRegion,
            limit: 500,
          }),
          getHotspotCells({
            region_id: selectedRegion,
            h3_res: selectedHexRes,
          }),
          getHistoryYearly({
            region_id: selectedRegion,
          }),
          getHarmonizationComparison({
            region_id: selectedRegion,
            granularity: 'week',
          }),
        ]);

        if (!active) return;

        setHotspots(hotspotResponse.data);
        setCells(cellResponse.data);
        setHistory(historyResponse.data);
        setComparison(comparisonResponse.data);

        setDataMode(hotspotResponse.meta?.data_mode ?? null);
        setIsSynthetic(hotspotResponse.meta?.is_synthetic ?? false);
      } catch (err) {
        if (!active) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load dashboard data.',
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    loadDashboard();

    return () => {
      active = false;
    };
  }, [selectedRegion, selectedHexRes]);

  const visibleHotspots = useMemo(() => {
    return (hotspots?.features ?? []).filter((feature) => {
      const sensor = feature.properties.sensor_family;

      if (sensor === 'MODIS' && !showModis) return false;
      if (sensor === 'VIIRS' && !showViirs) return false;

      return true;
    });
  }, [hotspots, showModis, showViirs]);

  const selectedCell = cells?.cells?.[0] ?? null;

  const totalHarmonized = useMemo(() => {
    const latestYear = history?.years?.at(-1);
    return latestYear ?? null;
  }, [history]);

  const latestComparison = comparison?.series?.at(-1) ?? null;

  const modisTotal = totalHarmonized?.modis_observed ?? null;
  const viirsTotal = totalHarmonized?.viirs_observed ?? null;
  const harmonizedTotal = totalHarmonized?.harmonized_value ?? null;

  const sensorTotal =
    (modisTotal ?? 0) + (viirsTotal ?? 0);

  const viirsShare =
    sensorTotal > 0 && viirsTotal !== null
      ? (viirsTotal / sensorTotal) * 100
      : null;

  const yearlyTrend = history?.years ?? [];

  return (
    <div className="flex flex-col w-full pb-12">
      {/* Dataset status */}
      <aside
        aria-label="Dataset status"
        className="w-full bg-[#0a0e18] px-6 py-2 flex flex-wrap items-center justify-between gap-2 border-b border-[#1F2937]"
      >
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded font-caption-mono text-[10px] uppercase tracking-wider font-bold ${
              isSynthetic
                ? 'bg-[#f59e0b] text-[#0B0F19]'
                : 'bg-[#7bd0ff]/20 text-[#7bd0ff]'
            }`}
          >
            {isSynthetic ? 'SYNTHETIC FIXTURE' : 'DATA SOURCE'}
          </span>

          <span className="font-caption-mono text-xs text-[#dfe2f1]">
            {dataMode ? `${dataMode.toUpperCase()} MODE` : 'Awaiting data'}
          </span>
        </div>

        <span className="font-caption-mono text-[10px] text-[#a08e7a]">
          {hotspots?.truncated
            ? 'Hotspot results are capped'
            : 'Dashboard data from configured API'}
        </span>
      </aside>

      <FilterBar />

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 p-3 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {error}
          <button
            type="button"
            onClick={() => setSelectedHexRes((value) => value)}
            className="ml-3 underline"
          >
            Reload page to retry
          </button>
        </div>
      )}

      {/* Headline metrics */}
      <section
        aria-label="Key observational metrics"
        className="w-full px-6 py-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Harmonized Fire Activity"
            value={formatNumber(harmonizedTotal)}
            description={
              totalHarmonized
                ? `Annual total • ${totalHarmonized.year}`
                : 'No annual data available'
            }
            accent="text-[#ffc174]"
          />

          <StatCard
            label="MODIS Observations"
            value={formatNumber(modisTotal)}
            unit="points"
            description="Latest available annual record"
            accent="text-[#ffbcb7]"
          />

          <StatCard
            label="VIIRS Observations"
            value={formatNumber(viirsTotal)}
            unit="points"
            description="Latest available annual record"
            accent="text-[#7bd0ff]"
          />

          <StatCard
            label="VIIRS Share of Raw Observations"
            value={viirsShare !== null ? `${viirsShare.toFixed(1)}%` : '—'}
            description="Share of MODIS + VIIRS observed counts"
            accent="text-[#ffddb8]"
          />
        </div>
      </section>

      {/* Main dashboard */}
      <div className="w-full px-6 flex-1 flex flex-col lg:flex-row gap-4">
        {/* Geospatial data panel */}
        <section
          aria-label="Hotspot and H3 cell data"
          className="lg:w-[65%] flex flex-col rounded bg-[#0a0e18] border border-[#1F2937] overflow-hidden shadow-xl min-h-[620px]"
        >
          {/* Map controls */}
          <div className="w-full px-4 py-3 bg-[#171b26] border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase mr-1">
                Data view:
              </span>

              {(['hex', 'raw', 'frp'] as Overlay[]).map((overlay) => (
                <button
                  key={overlay}
                  type="button"
                  onClick={() => setActiveOverlay(overlay)}
                  className={`px-2.5 py-1 rounded font-label-mono text-xs font-semibold transition-colors ${
                    activeOverlay === overlay
                      ? 'bg-[#f59e0b] text-[#0B0F19]'
                      : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
                  }`}
                >
                  {overlay === 'hex'
                    ? 'Harmonized Cells'
                    : overlay === 'raw'
                      ? 'Raw Hotspots'
                      : 'FRP'}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1 bg-[#1c1f2a] px-2 py-1 rounded border border-[#262a35]">
                <span className="font-caption-mono text-[10px] text-[#a08e7a]">
                  H3 RES:
                </span>

                {[6, 7, 8].map((resolution) => (
                  <button
                    key={resolution}
                    type="button"
                    onClick={() => setSelectedHexRes(resolution)}
                    className={`px-1.5 py-0.5 font-caption-mono text-[10px] font-bold rounded ${
                      selectedHexRes === resolution
                        ? 'bg-[#00a6e0] text-[#00374d]'
                        : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
                    }`}
                  >
                    {resolution}
                  </button>
                ))}
              </div>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showModis}
                  onChange={(e) => setShowModis(e.target.checked)}
                  className="accent-[#7bd0ff]"
                />
                <span className="font-caption-mono text-[10px] text-[#ffbcb7]">
                  MODIS
                </span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showViirs}
                  onChange={(e) => setShowViirs(e.target.checked)}
                  className="accent-[#f59e0b]"
                />
                <span className="font-caption-mono text-[10px] text-[#ffc174]">
                  VIIRS
                </span>
              </label>
            </div>
          </div>

          {/* Data display */}
          <div className="flex-1 p-4 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  {activeOverlay === 'hex'
                    ? 'H3 Harmonized Cell Aggregates'
                    : activeOverlay === 'raw'
                      ? 'Satellite Hotspot Observations'
                      : 'Fire Radiative Power Observations'}
                </h2>

                <p className="font-caption-mono text-[10px] text-[#a08e7a] mt-1">
                  Region:{' '}
                  {regions.find((r) => r.region_id === selectedRegion)?.name ??
                    'Loading region'}
                </p>
              </div>

              <span className="font-caption-mono text-[10px] text-[#7bd0ff]">
                {activeOverlay === 'hex'
                  ? `${cells?.cells?.length ?? 0} cells returned`
                  : `${visibleHotspots.length} observations returned`}
              </span>
            </div>

            {loading ? (
              <div className="flex-1 min-h-[300px] flex items-center justify-center text-[#7bd0ff] font-mono text-sm">
                Loading geospatial data...
              </div>
            ) : activeOverlay === 'hex' ? (
              <div className="overflow-x-auto rounded border border-[#262a35]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#171b26] text-[#a08e7a] font-caption-mono">
                    <tr>
                      <th className="p-3">H3 Cell</th>
                      <th className="p-3">Harmonized</th>
                      <th className="p-3">Lower</th>
                      <th className="p-3">Upper</th>
                      <th className="p-3">MODIS</th>
                      <th className="p-3">VIIRS</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(cells?.cells ?? []).map((cell) => (
                      <tr
                        key={cell.h3_cell}
                        className="border-t border-[#262a35] hover:bg-[#171b26]"
                      >
                        <td className="p-3 font-mono text-[#7bd0ff]">
                          {cell.h3_cell}
                        </td>
                        <td className="p-3 text-[#ffc174] font-bold">
                          {formatDecimal(cell.harmonized_value)}
                        </td>
                        <td className="p-3 text-[#dfe2f1]">
                          {formatDecimal(cell.lower)}
                        </td>
                        <td className="p-3 text-[#dfe2f1]">
                          {formatDecimal(cell.upper)}
                        </td>
                        <td className="p-3 text-[#ffbcb7]">
                          {formatNumber(cell.modis_observed)}
                        </td>
                        <td className="p-3 text-[#7bd0ff]">
                          {formatNumber(cell.viirs_observed)}
                        </td>
                      </tr>
                    ))}

                    {(!cells?.cells || cells.cells.length === 0) && (
                      <tr>
                        <td
                          colSpan={6}
                          className="p-6 text-center text-[#a08e7a]"
                        >
                          No H3 cell records returned for this selection.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="overflow-x-auto rounded border border-[#262a35]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#171b26] text-[#a08e7a] font-caption-mono">
                    <tr>
                      <th className="p-3">Observation</th>
                      <th className="p-3">Sensor</th>
                      <th className="p-3">Platform</th>
                      <th className="p-3">Coordinates</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">FRP (MW)</th>
                    </tr>
                  </thead>

                  <tbody>
                    {visibleHotspots
                      .filter((feature) => {
                        if (activeOverlay === 'frp') {
                          return feature.properties.frp_mw !== null &&
                            feature.properties.frp_mw !== undefined;
                        }

                        return true;
                      })
                      .map((feature, index) => (
                        <tr
                          key={feature.properties.obs_id ?? index}
                          className="border-t border-[#262a35] hover:bg-[#171b26]"
                        >
                          <td className="p-3 font-mono text-[#dfe2f1]">
                            {feature.properties.acq_datetime_utc}
                          </td>
                          <td
                            className={`p-3 font-bold ${
                              feature.properties.sensor_family === 'MODIS'
                                ? 'text-[#ffbcb7]'
                                : 'text-[#7bd0ff]'
                            }`}
                          >
                            {feature.properties.sensor_family}
                          </td>
                          <td className="p-3 text-[#dfe2f1]">
                            {feature.properties.platform ?? '—'}
                          </td>
                          <td className="p-3 font-mono text-[#a08e7a]">
                            {feature.geometry.coordinates[1].toFixed(3)},{' '}
                            {feature.geometry.coordinates[0].toFixed(3)}
                          </td>
                          <td className="p-3 text-[#dfe2f1]">
                            {feature.properties.confidence_class ?? '—'}
                          </td>
                          <td className="p-3 text-[#ffc174]">
                            {formatDecimal(feature.properties.frp_mw)}
                          </td>
                        </tr>
                      ))}

                    {visibleHotspots.length === 0 && (
                      <tr>
                        <td
                          colSpan={6}
                          className="p-6 text-center text-[#a08e7a]"
                        >
                          No observations match the selected sensor filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            <div className="rounded bg-[#171b26] border border-[#262a35] p-3">
              <p className="font-caption-mono text-[10px] text-[#a08e7a] leading-relaxed">
                {activeOverlay === 'hex'
                  ? 'H3 values represent harmonized cell aggregates. Lower and upper values show the returned uncertainty interval.'
                  : activeOverlay === 'raw'
                    ? 'Raw hotspot detections are individual satellite observations. MODIS and VIIRS counts are not directly interchangeable.'
                    : 'FRP is shown only where the source observation includes a reported FRP value. Missing FRP is not treated as zero.'}
              </p>
            </div>
          </div>
        </section>

        {/* Analytics panel */}
        <aside
          aria-label="Harmonization analytics"
          className="lg:w-[35%] flex flex-col gap-4"
        >
          {/* Selected cell */}
          <section className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md">
            <div className="flex items-center justify-between">
              <h2 className="font-title-sm text-sm text-[#dfe2f1] font-bold">
                Selected H3 Cell
              </h2>

              <span className="px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-[10px]">
                H3 Res {cells?.h3_resolution ?? selectedHexRes}
              </span>
            </div>

            {selectedCell ? (
              <>
                <p className="font-mono text-sm font-bold text-[#ffc174] mt-3 break-all">
                  {selectedCell.h3_cell}
                </p>

                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="bg-[#171b26] p-3 rounded">
                    <span className="font-caption-mono text-[9px] text-[#a08e7a] block">
                      HARMONIZED VALUE
                    </span>
                    <span className="font-mono text-lg text-[#ffc174] font-bold">
                      {formatDecimal(selectedCell.harmonized_value)}
                    </span>
                  </div>

                  <div className="bg-[#171b26] p-3 rounded">
                    <span className="font-caption-mono text-[9px] text-[#a08e7a] block">
                      MODIS OBSERVED
                    </span>
                    <span className="font-mono text-lg text-[#ffbcb7] font-bold">
                      {formatNumber(selectedCell.modis_observed)}
                    </span>
                  </div>

                  <div className="bg-[#171b26] p-3 rounded">
                    <span className="font-caption-mono text-[9px] text-[#a08e7a] block">
                      VIIRS OBSERVED
                    </span>
                    <span className="font-mono text-lg text-[#7bd0ff] font-bold">
                      {formatNumber(selectedCell.viirs_observed)}
                    </span>
                  </div>

                  <div className="bg-[#171b26] p-3 rounded">
                    <span className="font-caption-mono text-[9px] text-[#a08e7a] block">
                      UNCERTAINTY RANGE
                    </span>
                    <span className="font-mono text-sm text-[#dfe2f1] font-bold">
                      {formatDecimal(selectedCell.lower)} –{' '}
                      {formatDecimal(selectedCell.upper)}
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-xs text-[#a08e7a] mt-4">
                No cell selected or no cell data returned.
              </p>
            )}
          </section>

          {/* Temporal comparison */}
          <section className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-title-sm text-sm text-[#dfe2f1] font-bold">
                  Temporal Sensor Comparison
                </h2>
                <span className="font-caption-mono text-[9px] text-[#a08e7a]">
                  {comparison?.granularity ?? 'Weekly'} harmonized series
                </span>
              </div>

              <span className="px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-[10px]">
                API DATA
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {(comparison?.series ?? []).map((item) => {
                const max = Math.max(
                  item.modis_observed,
                  item.viirs_observed,
                  item.harmonized_value,
                  1,
                );

                return (
                  <div key={item.period}>
                    <div className="flex justify-between text-[10px] font-caption-mono mb-1">
                      <span className="text-[#a08e7a]">{item.period}</span>
                      <span className="text-[#ffc174]">
                        HAI: {formatNumber(item.harmonized_value)}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="h-1.5 rounded bg-[#0a0e18] overflow-hidden">
                        <div
                          className="h-full bg-[#ffbcb7]"
                          style={{
                            width: `${(item.modis_observed / max) * 100}%`,
                          }}
                        />
                      </div>

                      <div className="h-1.5 rounded bg-[#0a0e18] overflow-hidden">
                        <div
                          className="h-full bg-[#7bd0ff]"
                          style={{
                            width: `${(item.viirs_observed / max) * 100}%`,
                          }}
                        />
                      </div>

                      <div className="h-1.5 rounded bg-[#0a0e18] overflow-hidden">
                        <div
                          className="h-full bg-[#ffc174]"
                          style={{
                            width: `${(item.harmonized_value / max) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}

              {(!comparison?.series || comparison.series.length === 0) && (
                <p className="text-xs text-[#a08e7a]">
                  No comparison series returned.
                </p>
              )}
            </div>

            <div className="flex flex-wrap gap-3 mt-4 text-[9px] font-caption-mono text-[#a08e7a]">
              <span className="text-[#ffbcb7]">■ MODIS</span>
              <span className="text-[#7bd0ff]">■ VIIRS</span>
              <span className="text-[#ffc174]">■ Harmonized</span>
            </div>

            {latestComparison && (
              <div className="mt-3 pt-3 border-t border-[#262a35] text-xs text-[#d8c3ad]">
                Latest period: {latestComparison.period}
                <br />
                Harmonized interval:{' '}
                {formatNumber(latestComparison.lower)} –{' '}
                {formatNumber(latestComparison.upper)}
              </div>
            )}
          </section>

          {/* Harmonization note */}
          <section className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#ffc174] text-base">
                info
              </span>
              <h2 className="font-title-sm text-sm text-[#ffc174] font-bold">
                Why Raw Counts Cannot Be Added
              </h2>
            </div>

            <p className="font-body-sm text-[11px] text-[#d8c3ad] leading-relaxed mt-2">
              MODIS and VIIRS have different spatial resolutions,
              sensitivities and observation characteristics. Their raw
              detections are not interchangeable. Harmonized values should
              be interpreted using the calibration method and uncertainty
              information supplied by the backend.
            </p>
          </section>

          {/* Annual history */}
          <section className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md">
            <h2 className="font-title-sm text-sm text-[#dfe2f1] font-bold">
              Annual Harmonized Activity
            </h2>

            <div className="mt-4 space-y-3">
              {yearlyTrend.map((item) => {
                const max = Math.max(
                  ...yearlyTrend.map((year) => year.harmonized_value),
                  1,
                );

                return (
                  <div key={item.year}>
                    <div className="flex justify-between font-caption-mono text-[10px] mb-1">
                      <span className="text-[#a08e7a]">{item.year}</span>
                      <span className="text-[#dfe2f1]">
                        {formatNumber(item.harmonized_value)}
                      </span>
                    </div>

                    <div className="h-2 rounded bg-[#0a0e18] overflow-hidden">
                      <div
                        className="h-full rounded bg-[#f59e0b]"
                        style={{
                          width: `${(item.harmonized_value / max) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}

              {yearlyTrend.length === 0 && (
                <p className="text-xs text-[#a08e7a]">
                  No annual history returned.
                </p>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

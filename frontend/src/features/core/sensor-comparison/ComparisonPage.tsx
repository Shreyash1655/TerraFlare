
import { useCallback, useEffect, useMemo, useState } from 'react';
import MethodDrawer from '../../../components/provenance/MethodDrawer';
import {
  getRegions,
  getHarmonizationComparison,
  getHarmonizationMethod,
} from '../../../api/core';

type ComparisonData = Awaited<
  ReturnType<typeof getHarmonizationComparison>
>['data'];

type MethodData = Awaited<
  ReturnType<typeof getHarmonizationMethod>
>['data'];

type Region = Awaited<
  ReturnType<typeof getRegions>
>['data']['regions'][number];

const formatNumber = (value: number | null | undefined) => {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return `${(value * 100).toFixed(1)}%`;
};

export default function ComparisonPage() {
  const [selectedRegion, setSelectedRegion] = useState('pwn');
  const [regions, setRegions] = useState<Region[]>([]);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [method, setMethod] = useState<MethodData | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [regionsResponse, comparisonResponse, methodResponse] =
        await Promise.all([
          getRegions(),
          getHarmonizationComparison({
            region_id: selectedRegion,
            granularity: 'month',
          }),
          getHarmonizationMethod(),
        ]);

      setRegions(regionsResponse.data.regions);
      setComparison(comparisonResponse.data);
      setMethod(methodResponse.data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load harmonization comparison data.'
      );
    } finally {
      setLoading(false);
    }
  }, [selectedRegion]);

  useEffect(() => {
    void loadData();
  }, [loadData, reloadKey]);

  const series = comparison?.series ?? [];

  const chart = useMemo(() => {
    if (series.length === 0) {
      return null;
    }

    const values = series.flatMap((point) => [
      point.modis_observed,
      point.viirs_observed,
      point.harmonized_value,
      point.lower,
      point.upper,
    ]);

    const maximum = Math.max(...values, 1);
    const width = 700;
    const height = 230;
    const padding = 24;

    const x = (index: number) =>
      padding +
      (index / Math.max(series.length - 1, 1)) * (width - padding * 2);

    const y = (value: number) =>
      height -
      padding -
      (value / maximum) * (height - padding * 2);

    const makePath = (key: 'modis_observed' | 'viirs_observed' | 'harmonized_value') =>
      series
        .map(
          (point, index) =>
            `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point[key])}`
        )
        .join(' ');

    return {
      width,
      height,
      modis: makePath('modis_observed'),
      viirs: makePath('viirs_observed'),
      harmonized: makePath('harmonized_value'),
    };
  }, [series]);

  const diagnostics = comparison?.diagnostics;
  const overlap = diagnostics?.overlap_period;

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Header */}
      <section className="w-full px-6 pt-5 pb-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-2 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                NASA SPACE APPS 2026 • RECONCILIATION SUITE
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                H3-RES7 GRAIN
              </span>
            </div>

            <h1 className="text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              MODIS vs. VIIRS Statistical Calibration &amp; Harmonization
            </h1>

            <p className="text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Compare MODIS and VIIRS observations with the harmonized
              activity series. Both sensors have different spatial
              resolutions and detection characteristics, so their raw
              detection counts should not be directly added.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedRegion}
              onChange={(event) => setSelectedRegion(event.target.value)}
              className="bg-[#171b26] border border-[#374151] rounded px-3 py-2 text-xs text-[#dfe2f1] outline-none"
              aria-label="Select region"
            >
              {regions.map((region) => (
                <option key={region.region_id} value={region.region_id}>
                  {region.name}
                </option>
              ))}
            </select>

            <button
              onClick={() => setIsDrawerOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded bg-[#1c1f2a] hover:bg-[#262a35] text-[#dfe2f1] border border-[#374151] text-xs font-semibold transition-colors"
            >
              <span className="material-symbols-outlined text-[#7bd0ff] text-base">
                menu_book
              </span>
              Methodology
            </button>

            <button
              onClick={() => setReloadKey((value) => value + 1)}
              disabled={loading}
              className="flex items-center gap-2 px-3.5 py-2 rounded bg-[#f59e0b] text-[#0B0F19] text-xs font-bold hover:bg-[#ffb95f] disabled:opacity-50 transition-colors"
            >
              <span className="material-symbols-outlined text-base">
                refresh
              </span>
              Refresh data
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">
              Correlation
            </p>
            <p className="text-2xl font-bold text-[#7bd0ff] mt-1">
              {loading ? '...' : formatNumber(diagnostics?.correlation)}
            </p>
            <p className="text-[10px] text-[#a08e7a] mt-1">
              Backend-reported diagnostic
            </p>
          </div>

          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">
              Co-detection rate
            </p>
            <p className="text-2xl font-bold text-[#ffc174] mt-1">
              {loading ? '...' : formatPercent(diagnostics?.co_detection_rate)}
            </p>
            <p className="text-[10px] text-[#a08e7a] mt-1">
              When supplied by the backend
            </p>
          </div>

          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">
              Active method
            </p>
            <p className="text-lg font-bold text-[#dfe2f1] mt-2 truncate">
              {loading ? '...' : method?.method_id ?? '—'}
            </p>
            <p className="text-[10px] text-[#a08e7a] mt-1">
              Backend-reported method identifier
            </p>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="w-full px-6 py-6 space-y-6">
        {error && (
          <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
            <p className="text-sm text-red-300 font-semibold">
              Unable to load comparison data
            </p>
            <p className="text-xs text-red-200 mt-1">{error}</p>
            <button
              onClick={() => setReloadKey((value) => value + 1)}
              className="mt-3 text-xs text-[#ffc174] underline"
            >
              Try again
            </button>
          </div>
        )}

        {loading && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-10 text-center">
            <div className="animate-spin w-7 h-7 border-2 border-[#ffc174] border-t-transparent rounded-full mx-auto" />
            <p className="text-sm text-[#d8c3ad] mt-4">
              Loading harmonization comparison...
            </p>
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Time Series Chart */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5">
                <div>
                  <h2 className="text-base font-bold text-[#dfe2f1]">
                    Sensor Comparison Trajectory
                  </h2>
                  <p className="text-xs text-[#a08e7a] mt-1">
                    MODIS, VIIRS and harmonized observations over time
                  </p>
                </div>

                <span className="px-2 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] text-xs font-mono">
                  Granularity: {comparison?.granularity ?? '—'}
                </span>
              </div>

              {chart ? (
                <>
                  <div className="w-full overflow-x-auto">
                    <svg
                      viewBox={`0 0 ${chart.width} ${chart.height}`}
                      className="w-full min-w-[420px] h-64"
                      role="img"
                      aria-label="MODIS, VIIRS and harmonized time series comparison"
                    >
                      {[50, 100, 150, 200].map((position) => (
                        <line
                          key={position}
                          x1="24"
                          x2="676"
                          y1={position}
                          y2={position}
                          stroke="#313540"
                          strokeDasharray="4 4"
                        />
                      ))}

                      <path
                        d={chart.viirs}
                        fill="none"
                        stroke="#7bd0ff"
                        strokeWidth="2.5"
                      />

                      <path
                        d={chart.modis}
                        fill="none"
                        stroke="#ffbcb7"
                        strokeWidth="2.5"
                        strokeDasharray="5 4"
                      />

                      <path
                        d={chart.harmonized}
                        fill="none"
                        stroke="#ffc174"
                        strokeWidth="3"
                      />
                    </svg>
                  </div>

                  <div className="flex flex-wrap gap-5 text-xs mt-3">
                    <span className="flex items-center gap-2 text-[#ffc174]">
                      <span className="w-4 h-0.5 bg-[#ffc174]" />
                      Harmonized
                    </span>
                    <span className="flex items-center gap-2 text-[#7bd0ff]">
                      <span className="w-4 h-0.5 bg-[#7bd0ff]" />
                      VIIRS
                    </span>
                    <span className="flex items-center gap-2 text-[#ffbcb7]">
                      <span className="w-4 h-0.5 bg-[#ffbcb7]" />
                      MODIS
                    </span>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-sm text-[#a08e7a]">
                  No comparison series is available for this region.
                </div>
              )}
            </div>

            {/* Comparison Table */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5">
              <div className="mb-4">
                <h2 className="text-base font-bold text-[#dfe2f1]">
                  Harmonization Time-Series Records
                </h2>
                <p className="text-xs text-[#a08e7a] mt-1">
                  Values returned by the comparison API
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                      <th className="p-3">Period</th>
                      <th className="p-3 text-right">MODIS</th>
                      <th className="p-3 text-right">VIIRS</th>
                      <th className="p-3 text-right">Harmonized</th>
                      <th className="p-3 text-right">Lower</th>
                      <th className="p-3 text-right">Upper</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-[#262a35]">
                    {series.map((point, index) => (
                      <tr
                        key={`${point.period}-${index}`}
                        className="text-[#dfe2f1] hover:bg-[#262a35]/50"
                      >
                        <td className="p-3 font-mono text-[#7bd0ff]">
                          {point.period}
                        </td>
                        <td className="p-3 text-right">
                          {formatNumber(point.modis_observed)}
                        </td>
                        <td className="p-3 text-right">
                          {formatNumber(point.viirs_observed)}
                        </td>
                        <td className="p-3 text-right text-[#ffc174] font-semibold">
                          {formatNumber(point.harmonized_value)}
                        </td>
                        <td className="p-3 text-right">
                          {formatNumber(point.lower)}
                        </td>
                        <td className="p-3 text-right">
                          {formatNumber(point.upper)}
                        </td>
                      </tr>
                    ))}

                    {series.length === 0 && (
                      <tr>
                        <td
                          colSpan={6}
                          className="p-8 text-center text-[#a08e7a]"
                        >
                          No records available.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Method Details */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5">
              <h2 className="text-base font-bold text-[#dfe2f1] mb-3">
                Calibration Method &amp; Validation
              </h2>

              <p className="text-sm text-[#d8c3ad] leading-relaxed">
                {method?.description ?? 'No method description is available.'}
              </p>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">
                    Overlap period
                  </h3>
                  <p className="text-sm text-[#dfe2f1]">
                    {overlap?.start ?? method?.overlap_period?.start ?? '—'}
                    {' → '}
                    {overlap?.end ?? method?.overlap_period?.end ?? '—'}
                  </p>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">
                    Validation metrics
                  </h3>

                  {method?.validation?.length ? (
                    <div className="space-y-2">
                      {method.validation.map((item, index) => (
                        <div
                          key={`${item.metric}-${index}`}
                          className="flex justify-between gap-3 text-xs border-b border-[#313540] pb-2"
                        >
                          <span className="text-[#d8c3ad]">
                            {item.metric}
                          </span>
                          <span className="text-[#ffc174] font-mono">
                            {formatNumber(item.value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-[#a08e7a]">
                      No validation metrics available.
                    </p>
                  )}
                </div>

                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">
                    Assumptions
                  </h3>
                  <ul className="space-y-2">
                    {(method?.assumptions ?? []).map((item, index) => (
                      <li
                        key={index}
                        className="text-xs text-[#d8c3ad] list-disc ml-4"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">
                    Limitations
                  </h3>
                  <ul className="space-y-2">
                    {(method?.limitations ?? []).map((item, index) => (
                      <li
                        key={index}
                        className="text-xs text-[#d8c3ad] list-disc ml-4"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      <MethodDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}

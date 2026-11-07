
import { useEffect, useMemo, useState } from 'react';
import ExportButton from '../export/ExportButton';
import {
  getHistoryYearly,
  getHistoryMonthly,
  getRegions,
} from '../../../api/core';

type YearlyData = Awaited<ReturnType<typeof getHistoryYearly>>['data'];
type MonthlyData = Awaited<ReturnType<typeof getHistoryMonthly>>['data'];
type RegionsData = Awaited<ReturnType<typeof getRegions>>['data'];

type SensorView = 'harmonized' | 'all';

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

const formatNumber = (value: number | null | undefined) =>
  value == null ? '—' : Math.round(value).toLocaleString('en-IN');

const formatCompact = (value: number | null | undefined) => {
  if (value == null) return '—';
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k`;
  }
  return value.toFixed(0);
};

export default function HistoryPage() {
  const [selectedRegion, setSelectedRegion] = useState('pwn');
  const [selectedSensorView, setSelectedSensorView] =
    useState<SensorView>('harmonized');

  const [yearly, setYearly] = useState<YearlyData | null>(null);
  const [monthly, setMonthly] = useState<MonthlyData | null>(null);
  const [regions, setRegions] = useState<RegionsData['regions']>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError('');

      try {
        const [regionResponse, yearlyResponse, monthlyResponse] =
          await Promise.all([
            getRegions(),
            getHistoryYearly({ region_id: selectedRegion }),
            getHistoryMonthly({ region_id: selectedRegion }),
          ]);

        if (cancelled) return;

        setRegions(regionResponse.data.regions);
        setYearly(yearlyResponse.data);
        setMonthly(monthlyResponse.data);
      } catch (err) {
        if (cancelled) return;

        console.error('Failed to load historical data:', err);

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load historical data.'
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [selectedRegion, reloadKey]);

  const annualRows = yearly?.years ?? [];
  const monthlyRows = monthly?.matrix ?? [];

  const firstYear = annualRows[0]?.year;
  const lastYear = annualRows.length
    ? annualRows[annualRows.length - 1].year
    : undefined;

  const meanActivity = useMemo(() => {
    if (!annualRows.length) return null;

    const total = annualRows.reduce(
      (sum, row) => sum + row.harmonized_value,
      0
    );

    return total / annualRows.length;
  }, [annualRows]);

  const chartMaximum = useMemo(() => {
    if (!annualRows.length) return 1;

    if (selectedSensorView === 'harmonized') {
      return Math.max(
        1,
        ...annualRows.map((row) => row.harmonized_value)
      ) * 1.2;
    }

    return Math.max(
      1,
      ...annualRows.flatMap((row) => [
        row.modis_observed,
        row.viirs_observed,
      ])
    ) * 1.2;
  }, [annualRows, selectedSensorView]);

  const monthlyMaximum = useMemo(() => {
    if (!monthlyRows.length) return 1;

    return Math.max(
      1,
      ...monthlyRows.map((row) => row.harmonized_value)
    );
  }, [monthlyRows]);

  const monthlyByYear = useMemo(() => {
    const result = new Map<number, Map<number, (typeof monthlyRows)[number]>>();

    for (const row of monthlyRows) {
      if (!result.has(row.year)) {
        result.set(row.year, new Map());
      }

      result.get(row.year)?.set(row.month, row);
    }

    return result;
  }, [monthlyRows]);

  const regionName =
    regions.find((region) => region.region_id === selectedRegion)?.name ??
    selectedRegion;

  const exportStartDate = firstYear
    ? `${firstYear}-01-01`
    : '2020-01-01';

  const exportEndDate = lastYear
    ? `${lastYear}-12-31`
    : '2025-12-31';

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Header */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                LONGITUDINAL CLIMATOLOGY
              </span>

              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>

              <span className="font-caption-mono text-xs text-[#ffc174]">
                HISTORICAL TIME SERIES
              </span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Historical Year-Wise &amp; Month-Wise Analysis
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Explore annual harmonized activity and monthly climatological
              patterns using the available MODIS and VIIRS historical data.
              Sensor observations are displayed separately from harmonized
              estimates.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <ExportButton
              dataset="monthly"
              regionId={selectedRegion}
              startDate={exportStartDate}
              endDate={exportEndDate}
            />
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-5 border-t border-[#262a35] mt-4">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#7bd0ff] text-sm">
                location_on
              </span>

              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
                disabled={isLoading && regions.length === 0}
              >
                {regions.length === 0 && (
                  <option value="pwn" className="bg-[#171b26]">
                    Western North America (PacNW)
                  </option>
                )}

                {regions.map((region) => (
                  <option
                    key={region.region_id}
                    value={region.region_id}
                    className="bg-[#171b26]"
                  >
                    {region.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center bg-[#171b26] p-0.5 rounded border border-[#262a35]">
              <button
                onClick={() => setSelectedSensorView('harmonized')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedSensorView === 'harmonized'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Harmonized Index (HAI)
              </button>

              <button
                onClick={() => setSelectedSensorView('all')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedSensorView === 'all'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Sensor Decomposition
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 font-caption-mono text-xs text-[#a08e7a]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
            <span>{regionName}</span>
          </div>
        </div>
      </section>

      {/* Loading */}
      {isLoading && (
        <div className="px-6 py-20 flex flex-col items-center gap-3 text-[#a08e7a]">
          <span className="material-symbols-outlined animate-spin text-3xl text-[#f59e0b]">
            progress_activity
          </span>
          <p className="font-caption-mono text-xs">
            LOADING HISTORICAL DATA...
          </p>
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="mx-6 mt-6 p-5 rounded-lg border border-red-500/30 bg-red-500/5">
          <div className="flex items-center gap-2 text-red-400 mb-2">
            <span className="material-symbols-outlined">error</span>
            <span className="font-label-mono text-sm font-bold">
              HISTORICAL DATA UNAVAILABLE
            </span>
          </div>

          <p className="text-sm text-[#d8c3ad] mb-4">{error}</p>

          <button
            type="button"
            onClick={() => setReloadKey((value) => value + 1)}
            className="px-4 py-2 rounded bg-[#f59e0b] text-[#0B0F19] text-xs font-bold"
          >
            Retry
          </button>
        </div>
      )}

      {/* Analysis */}
      {!isLoading && !error && (
        <div className="w-full px-6 py-6 space-y-6">
          {/* Annual Chart */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#262a35] mb-4">
              <div>
                <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  {selectedSensorView === 'harmonized'
                    ? 'Annual Harmonized Activity'
                    : 'Annual Sensor Observation Counts'}
                </h2>

                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  {firstYear && lastYear
                    ? `${firstYear}–${lastYear}`
                    : 'Available historical period'}
                </span>
              </div>

              {selectedSensorView === 'harmonized' && meanActivity !== null && (
                <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
                  MEAN: {formatCompact(meanActivity)} / yr
                </span>
              )}
            </div>

            {annualRows.length === 0 ? (
              <p className="text-center py-16 text-[#a08e7a] text-sm">
                No annual historical records are available for this region.
              </p>
            ) : (
              <>
                <div className="w-full min-h-[260px] bg-[#0a0e18] rounded p-4 border border-[#262a35]">
                  <svg
                    className="w-full h-64"
                    preserveAspectRatio="none"
                    viewBox={`0 0 ${Math.max(800, annualRows.length * 90)} 260`}
                  >
                    {[50, 100, 150, 200].map((y) => (
                      <line
                        key={y}
                        stroke="#262a35"
                        strokeDasharray="3,3"
                        x1="0"
                        x2={Math.max(800, annualRows.length * 90)}
                        y1={y}
                        y2={y}
                      />
                    ))}

                    {annualRows.map((row, index) => {
                      const groupWidth = Math.max(
                        50,
                        760 / annualRows.length
                      );
                      const x = 20 + index * groupWidth;
                      const baseY = 220;

                      if (selectedSensorView === 'harmonized') {
                        const height =
                          (row.harmonized_value / chartMaximum) * 180;

                        const lowerY =
                          row.lower != null
                            ? baseY - (row.lower / chartMaximum) * 180
                            : null;

                        const upperY =
                          row.upper != null
                            ? baseY - (row.upper / chartMaximum) * 180
                            : null;

                        return (
                          <g key={row.year}>
                            {lowerY !== null && upperY !== null && (
                              <line
                                stroke="#ffc174"
                                strokeWidth="2"
                                x1={x + 20}
                                x2={x + 20}
                                y1={upperY}
                                y2={lowerY}
                              />
                            )}

                            <rect
                              x={x}
                              y={baseY - height}
                              width="40"
                              height={height}
                              rx="2"
                              fill="#f59e0b"
                              opacity="0.85"
                            />

                            <text
                              x={x + 20}
                              y="245"
                              fill="#a08e7a"
                              fontSize="11"
                              textAnchor="middle"
                              fontFamily="JetBrains Mono"
                            >
                              {row.year}
                            </text>
                          </g>
                        );
                      }

                      const modisHeight =
                        (row.modis_observed / chartMaximum) * 180;

                      const viirsHeight =
                        (row.viirs_observed / chartMaximum) * 180;

                      return (
                        <g key={row.year}>
                          <rect
                            x={x}
                            y={baseY - modisHeight}
                            width="18"
                            height={modisHeight}
                            rx="2"
                            fill="#7bd0ff"
                            opacity="0.9"
                          />

                          <rect
                            x={x + 21}
                            y={baseY - viirsHeight}
                            width="18"
                            height={viirsHeight}
                            rx="2"
                            fill="#f59e0b"
                            opacity="0.9"
                          />

                          <text
                            x={x + 20}
                            y="245"
                            fill="#a08e7a"
                            fontSize="11"
                            textAnchor="middle"
                            fontFamily="JetBrains Mono"
                          >
                            {row.year}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 font-caption-mono text-xs text-[#a08e7a]">
                  <span>
                    {selectedSensorView === 'harmonized'
                      ? 'Harmonized estimates with available uncertainty intervals'
                      : 'Raw observation counts shown separately by sensor'}
                  </span>

                  <div className="flex items-center gap-4">
                    {selectedSensorView === 'harmonized' ? (
                      <span className="flex items-center gap-1.5 text-[#ffc174]">
                        <span className="w-3 h-3 rounded-sm bg-[#f59e0b]" />
                        Harmonized Total
                      </span>
                    ) : (
                      <>
                        <span className="flex items-center gap-1.5 text-[#7bd0ff]">
                          <span className="w-3 h-3 rounded-sm bg-[#7bd0ff]" />
                          MODIS
                        </span>

                        <span className="flex items-center gap-1.5 text-[#ffc174]">
                          <span className="w-3 h-3 rounded-sm bg-[#f59e0b]" />
                          VIIRS
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Annual Data Table */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <div className="pb-3 border-b border-[#262a35] mb-4">
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">
                Annual Historical Records
              </h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">
                API-reported annual values and sensor observations
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-caption-mono text-xs border-collapse">
                <thead>
                  <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                    <th className="py-3 px-3">Year</th>
                    <th className="py-3 px-3 text-right">Harmonized</th>
                    <th className="py-3 px-3 text-right">Lower</th>
                    <th className="py-3 px-3 text-right">Upper</th>
                    <th className="py-3 px-3 text-right">MODIS Raw</th>
                    <th className="py-3 px-3 text-right">VIIRS Raw</th>
                    <th className="py-3 px-3 text-right">Sensor Mix</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#262a35]">
                  {annualRows.map((row) => (
                    <tr
                      key={row.year}
                      className="bg-[#171b26] hover:bg-[#262a35]/60"
                    >
                      <td className="py-3 px-3 font-bold text-[#dfe2f1]">
                        {row.year}
                      </td>

                      <td className="py-3 px-3 text-right text-[#ffc174]">
                        {formatNumber(row.harmonized_value)}
                      </td>

                      <td className="py-3 px-3 text-right text-[#a08e7a]">
                        {formatNumber(row.lower)}
                      </td>

                      <td className="py-3 px-3 text-right text-[#a08e7a]">
                        {formatNumber(row.upper)}
                      </td>

                      <td className="py-3 px-3 text-right text-[#7bd0ff]">
                        {formatNumber(row.modis_observed)}
                      </td>

                      <td className="py-3 px-3 text-right text-[#ffc174]">
                        {formatNumber(row.viirs_observed)}
                      </td>

                      <td className="py-3 px-3 text-right text-[#d8c3ad]">
                        {row.sensor_mix ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Monthly Heatmap */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#262a35] mb-4">
              <div>
                <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  Year × Month Harmonized Activity Heatmap
                </h2>

                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  Monthly aggregated harmonized activity across available years
                </span>
              </div>

              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                {monthlyRows.length} MONTHLY RECORDS
              </span>
            </div>

            {monthlyRows.length === 0 ? (
              <p className="text-center py-12 text-[#a08e7a] text-sm">
                No monthly records are available for this region.
              </p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-center font-caption-mono text-xs border-collapse">
                    <thead>
                      <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                        <th className="py-2 px-3 text-left">Year</th>

                        {MONTHS.map((month) => (
                          <th key={month} className="py-2 px-2">
                            {month}
                          </th>
                        ))}

                        <th className="py-2 px-3 text-right">Annual Total</th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-[#262a35]">
                      {Array.from(monthlyByYear.entries())
                        .sort(([a], [b]) => a - b)
                        .map(([year, monthMap]) => {
                          const yearRows = Array.from(monthMap.values());

                          const annualTotal = yearRows.reduce(
                            (sum, row) => sum + row.harmonized_value,
                            0
                          );

                          return (
                            <tr
                              key={year}
                              className="bg-[#171b26] hover:bg-[#262a35]/60"
                            >
                              <td className="py-2.5 px-3 text-left font-bold text-[#dfe2f1]">
                                {year}
                              </td>

                              {Array.from({ length: 12 }, (_, index) => {
                                const monthNumber = index + 1;
                                const value = monthMap.get(monthNumber);

                                if (!value) {
                                  return (
                                    <td
                                      key={monthNumber}
                                      className="py-2 px-1"
                                    >
                                      <span className="inline-block w-full rounded bg-[#262a35]/50 text-[#666] px-1 py-1">
                                        —
                                      </span>
                                    </td>
                                  );
                                }

                                const intensity = Math.max(
                                  0.12,
                                  value.harmonized_value / monthlyMaximum
                                );

                                return (
                                  <td
                                    key={monthNumber}
                                    className="py-2 px-1"
                                    title={`${MONTHS[index]} ${year}: ${formatNumber(value.harmonized_value)}${value.is_partial ? ' (partial)' : ''}`}
                                  >
                                    <span
                                      className="inline-block px-1.5 py-1 rounded text-[10px] text-[#0B0F19] font-bold"
                                      style={{
                                        backgroundColor: `rgba(245, 158, 11, ${Math.min(1, intensity)})`,
                                      }}
                                    >
                                      {formatCompact(value.harmonized_value)}
                                    </span>

                                    {value.is_partial && (
                                      <span className="block text-[8px] text-[#7bd0ff] mt-0.5">
                                        PARTIAL
                                      </span>
                                    )}
                                  </td>
                                );
                              })}

                              <td className="py-2.5 px-3 text-right font-bold text-[#ffc174]">
                                {formatNumber(annualTotal)}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-[#a08e7a] font-caption-mono text-[10px]">
                  <span>
                    Brighter cells indicate higher harmonized activity.
                  </span>
                  <span>
                    — = No monthly record available
                  </span>
                  <span>
                    PARTIAL = Incomplete period
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

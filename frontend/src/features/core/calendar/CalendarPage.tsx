
import { useEffect, useMemo, useState } from 'react';
import {
  getCalendar,
  getRegions,
  getCurrentVsMedian,
  getHistoryYearly,
} from '../../../api/core';

const months = [
  'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
  'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
];

type CalendarDay = {
  date: string;
  harmonized_value: number | null;
  lower: number | null;
  upper: number | null;
  data_flag?: string;
};

type Region = {
  region_id: string;
  name: string;
};

type Comparison = {
  year: number;
  month: number;
  is_partial: boolean;
  current: number | null;
  median: number | null;
  q25: number | null;
  q75: number | null;
  n_baseline_years: number;
  ratio_to_median: number | null;
};

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return Math.round(value).toLocaleString('en-IN');
}

function getMonthDays(year: number, monthIndex: number) {
  return new Date(year, monthIndex + 1, 0).getDate();
}

function getDayColor(day: CalendarDay | undefined) {
  if (!day) return 'bg-[#111827] border border-dashed border-[#303746]';

  if (day.data_flag === 'no_data' || day.data_flag === 'low_coverage') {
    return 'bg-[#111827] border border-dashed border-[#596273]';
  }

  const value = day.harmonized_value;

  if (value === null || value === undefined) {
    return 'bg-[#111827] border border-dashed border-[#303746]';
  }

  if (value === 0) return 'bg-[#1c1f2a]';

  if (value < 50) return 'bg-[#7bd0ff]/30';
  if (value < 150) return 'bg-[#7bd0ff]/60';
  if (value < 300) return 'bg-[#ffc174]/70';

  return 'bg-[#f59e0b]';
}

function AppLoading() {
  return (
    <div className="min-h-[300px] flex items-center justify-center text-[#7bd0ff] font-mono text-sm">
      Loading calendar data...
    </div>
  );
}

export default function CalendarPage() {
  const [selectedYear, setSelectedYear] = useState(2026);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedMetric, setSelectedMetric] = useState<'hai' | 'frp'>('hai');

  const [regions, setRegions] = useState<Region[]>([]);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);

  const [unit, setUnit] = useState('harmonized activity index');
  const [dataMode, setDataMode] = useState<'fixture' | 'real' | null>(null);
  const [isSynthetic, setIsSynthetic] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load regions and available historical years.
  useEffect(() => {
    let active = true;

    async function loadInitialData() {
      try {
        const [regionResponse, historyResponse] = await Promise.all([
          getRegions(),
          getHistoryYearly(),
        ]);

        if (!active) return;

        const regionList = (regionResponse.data as any).regions ?? [];
        const yearList = ((historyResponse.data as any).years ?? [])
          .map((item: any) => Number(item.year))
          .filter((year: number) => Number.isFinite(year));

        setRegions(regionList);

        const firstRegion = regionList[0]?.region_id ?? '';
        setSelectedRegion(firstRegion);

        const uniqueYears = [...new Set<number>(yearList)].sort(
          (a, b) => b - a,
        );

        setAvailableYears(uniqueYears);

        if (uniqueYears.length > 0) {
          setSelectedYear(uniqueYears[0]);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load calendar filters.',
          );
        }
      }
    }

    loadInitialData();

    return () => {
      active = false;
    };
  }, []);

  // Load calendar and current-vs-median data.
  useEffect(() => {
    if (!selectedRegion) return;

    let active = true;

    async function loadCalendarData() {
      setLoading(true);
      setError('');

      try {
        const [calendarResponse, comparisonResponse] = await Promise.all([
          getCalendar({
            region_id: selectedRegion,
            year: selectedYear,
          }),
          getCurrentVsMedian({
            region_id: selectedRegion,
          }),
        ]);

        if (!active) return;

        const calendarData = calendarResponse.data as any;
        const comparisonData = comparisonResponse.data as Comparison;

        setDays(calendarData.days ?? []);
        setUnit(calendarData.unit ?? 'harmonized activity index');
        setComparison(comparisonData);

        setDataMode(calendarResponse.meta?.data_mode ?? null);
        setIsSynthetic(calendarResponse.meta?.is_synthetic ?? false);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load calendar data.',
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadCalendarData();

    return () => {
      active = false;
    };
  }, [selectedRegion, selectedYear]);

  const dayMap = useMemo(() => {
    const map = new Map<string, CalendarDay>();

    days.forEach((day) => {
      map.set(day.date, day);
    });

    return map;
  }, [days]);

  const statistics = useMemo(() => {
    const validDays = days.filter(
      (day) =>
        day.harmonized_value !== null &&
        day.harmonized_value !== undefined,
    );

    const total = validDays.reduce(
      (sum, day) => sum + (day.harmonized_value ?? 0),
      0,
    );

    const peakDay = validDays.reduce<CalendarDay | null>(
      (peak, day) =>
        !peak ||
        (day.harmonized_value ?? 0) >
          (peak.harmonized_value ?? 0)
          ? day
          : peak,
      null,
    );

    return {
      total,
      peakDay,
      availableDays: validDays.length,
    };
  }, [days]);

  const comparisonRatio =
    comparison?.ratio_to_median !== null &&
    comparison?.ratio_to_median !== undefined
      ? comparison.ratio_to_median
      : null;

  const comparisonPosition = useMemo(() => {
    if (
      !comparison ||
      comparison.current === null ||
      comparison.q25 === null ||
      comparison.q75 === null
    ) {
      return null;
    }

    const maxValue = Math.max(
      comparison.current,
      comparison.q75,
      comparison.median ?? 0,
      1,
    );

    return {
      q25: (comparison.q25 / maxValue) * 100,
      q75: (comparison.q75 / maxValue) * 100,
      median:
        comparison.median !== null
          ? (comparison.median / maxValue) * 100
          : null,
      current: (comparison.current / maxValue) * 100,
    };
  }, [comparison]);

  if (loading && days.length === 0) {
    return <AppLoading />;
  }

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Header and controls */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div className="flex flex-col max-w-3xl">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-[#f59e0b] animate-pulse" />
              <span className="font-label-mono text-[10px] text-[#ffc174] uppercase tracking-widest font-semibold">
                MISSION TELEMETRY • SUBSYSTEM 03
              </span>
              {dataMode && (
                <span className="text-[#a08e7a] font-caption-mono text-xs">
                  | {dataMode.toUpperCase()} DATA
                </span>
              )}
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Historical Burning Activity Calendar &amp; Multi-Year Climatology Matrix
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] mt-1 leading-relaxed">
              Daily harmonized satellite fire activity with uncertainty
              intervals and historical comparisons.
            </p>

            {isSynthetic && (
              <span className="mt-2 text-xs text-[#ffc174]">
                Synthetic demonstration data — not observed fire activity.
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 bg-[#171b26] p-1.5 rounded-lg border border-[#262a35]">
            {/* Region selector */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c1f2a] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#7bd0ff] text-sm">
                travel_explore
              </span>

              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              >
                {regions.map((region) => (
                  <option
                    key={region.region_id}
                    value={region.region_id}
                    className="bg-[#1c1f2a]"
                  >
                    {region.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Year selector */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c1f2a] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#ffc174] text-sm">
                history_edu
              </span>

              <label className="font-caption-mono text-[10px] text-[#a08e7a]">
                YEAR:
              </label>

              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="bg-transparent font-label-mono text-xs text-[#ffc174] font-semibold focus:outline-none cursor-pointer"
              >
                {availableYears.map((year) => (
                  <option
                    key={year}
                    value={year}
                    className="bg-[#1c1f2a]"
                  >
                    {year}
                  </option>
                ))}
              </select>
            </div>

            {/* Metric selector */}
            <div className="flex items-center bg-[#1c1f2a] p-0.5 rounded border border-[#262a35]">
              <button
                onClick={() => setSelectedMetric('hai')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedMetric === 'hai'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Harmonized HAI
              </button>

              <button
                onClick={() => setSelectedMetric('frp')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedMetric === 'frp'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                FRP (MW)
              </button>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 p-3 rounded border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
            {error}
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="ml-3 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-5">
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Annual Harmonized Total
            </span>
            <div className="font-mono-metric-lg text-2xl font-bold text-[#ffc174] mt-1">
              {formatNumber(statistics.total)}
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">
              {unit}
            </span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Peak Recorded Day
            </span>
            <div className="font-mono-metric-lg text-xl font-bold text-[#dfe2f1] mt-1">
              {statistics.peakDay?.date ?? '—'}
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">
              {formatNumber(statistics.peakDay?.harmonized_value)} activity
            </span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Current vs Median
            </span>
            <div className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff] mt-1">
              {comparisonRatio !== null
                ? `${comparisonRatio.toFixed(2)}x`
                : '—'}
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">
              Historical comparison
            </span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Available Daily Records
            </span>
            <div className="font-mono-metric-lg text-2xl font-bold text-[#ffddb8] mt-1">
              {statistics.availableDays}
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">
              Days with reported values
            </span>
          </div>
        </div>
      </section>

      {/* Calendar heatmap */}
      <section className="w-full px-6 py-6 space-y-6">
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#262a35] gap-2">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1] flex items-center gap-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">
                  calendar_month
                </span>
                Daily Burning Activity Heatmap ({selectedYear})
              </h2>

              <span className="font-caption-mono text-xs text-[#a08e7a]">
                Daily satellite-derived activity and reported uncertainty
              </span>
            </div>
          </div>

          {selectedMetric === 'frp' ? (
            <div className="mt-6 p-5 rounded bg-[#0a0e18] border border-[#262a35] text-sm text-[#a08e7a]">
              FRP is not provided by the current daily calendar API. The
              heatmap displays harmonized activity only.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-4">
                {months.map((month, monthIndex) => {
                  const numberOfDays = getMonthDays(
                    selectedYear,
                    monthIndex,
                  );

                  const firstWeekday = new Date(
                    selectedYear,
                    monthIndex,
                    1,
                  ).getDay();

                  return (
                    <div
                      key={month}
                      className="bg-[#171b26] p-3 rounded border border-[#262a35]"
                    >
                      <div className="flex justify-between items-center mb-3 font-caption-mono text-xs">
                        <span className="font-bold text-[#dfe2f1]">
                          {month}
                        </span>
                        <span className="text-[#a08e7a]">
                          {numberOfDays} days
                        </span>
                      </div>

                      <div className="grid grid-cols-7 gap-1 mb-1">
                        {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map(
                          (weekday, index) => (
                            <span
                              key={`${weekday}-${index}`}
                              className="text-center text-[9px] text-[#a08e7a]"
                            >
                              {weekday}
                            </span>
                          ),
                        )}
                      </div>

                      <div className="grid grid-cols-7 gap-1">
                        {Array.from({ length: firstWeekday }).map(
                          (_, index) => (
                            <div key={`empty-${index}`} />
                          ),
                        )}

                        {Array.from({ length: numberOfDays }).map(
                          (_, dayIndex) => {
                            const date = `${selectedYear}-${String(
                              monthIndex + 1,
                            ).padStart(2, '0')}-${String(
                              dayIndex + 1,
                            ).padStart(2, '0')}`;

                            const day = dayMap.get(date);

                            return (
                              <div
                                key={date}
                                title={
                                  day
                                    ? `${date} | Activity: ${formatNumber(
                                        day.harmonized_value,
                                      )} | Interval: ${formatNumber(
                                        day.lower,
                                      )}–${formatNumber(day.upper)}`
                                    : `${date} | No data returned`
                                }
                                className={`relative aspect-square rounded-sm ${getDayColor(
                                  day,
                                )} hover:ring-2 hover:ring-[#7bd0ff] transition-all`}
                              >
                                <span className="absolute inset-0 flex items-center justify-center text-[8px] text-[#dfe2f1]/80">
                                  {dayIndex + 1}
                                </span>
                              </div>
                            );
                          },
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 mt-4 border-t border-[#262a35] font-caption-mono text-xs text-[#a08e7a]">
                <span>Lower activity</span>

                <div className="flex items-center gap-1">
                  <span className="w-4 h-3 bg-[#1c1f2a] rounded-sm" />
                  <span className="w-4 h-3 bg-[#7bd0ff]/30 rounded-sm" />
                  <span className="w-4 h-3 bg-[#7bd0ff]/60 rounded-sm" />
                  <span className="w-4 h-3 bg-[#ffc174]/70 rounded-sm" />
                  <span className="w-4 h-3 bg-[#f59e0b] rounded-sm" />
                  <span className="w-4 h-3 bg-[#111827] border border-dashed border-[#596273] rounded-sm" />
                </div>

                <span>Higher activity / No data</span>
              </div>
            </>
          )}
        </div>

        {/* Current month vs historical median */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
            <div>
              <h3 className="font-title-sm text-base font-bold text-[#dfe2f1]">
                Current Month vs Historical Median
              </h3>
              <span className="font-caption-mono text-xs text-[#a08e7a]">
                Comparison against the historical distribution for the same
                calendar month
              </span>
            </div>

            {comparison && (
              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
                {months[comparison.month - 1] ?? 'MONTH'}
              </span>
            )}
          </div>

          {!comparison ? (
            <p className="mt-5 text-sm text-[#a08e7a]">
              Historical comparison is not available.
            </p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
              <div className="space-y-3">
                <div className="flex justify-between font-caption-mono text-xs">
                  <span className="text-[#a08e7a]">Historical Median:</span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(comparison.median)}
                  </span>
                </div>

                <div className="flex justify-between font-caption-mono text-xs">
                  <span className="text-[#a08e7a]">Interquartile Range:</span>
                  <span className="text-[#7bd0ff] font-bold">
                    [{formatNumber(comparison.q25)} –{' '}
                    {formatNumber(comparison.q75)}]
                  </span>
                </div>

                <div className="flex justify-between font-caption-mono text-xs">
                  <span className="text-[#a08e7a]">Current Activity:</span>
                  <span className="text-[#ffc174] font-bold">
                    {formatNumber(comparison.current)}
                  </span>
                </div>

                <div className="flex justify-between font-caption-mono text-xs">
                  <span className="text-[#a08e7a]">Baseline Years:</span>
                  <span className="text-[#dfe2f1] font-bold">
                    {comparison.n_baseline_years}
                  </span>
                </div>

                {comparison.is_partial && (
                  <p className="text-xs text-[#ffc174]">
                    Current month is partial. Interpret the comparison
                    accordingly.
                  </p>
                )}
              </div>

              <div className="lg:col-span-2 flex flex-col justify-center space-y-3">
                {comparisonPosition ? (
                  <>
                    <div className="relative w-full h-8 bg-[#0a0e18] rounded-lg border border-[#262a35] overflow-hidden">
                      <div
                        className="absolute h-full bg-[#7bd0ff]/20 border-x border-[#7bd0ff]/40"
                        style={{
                          left: `${comparisonPosition.q25}%`,
                          width: `${Math.max(
                            0,
                            comparisonPosition.q75 -
                              comparisonPosition.q25,
                          )}%`,
                        }}
                      />

                      {comparisonPosition.median !== null && (
                        <div
                          className="absolute top-0 h-full w-0.5 bg-[#dfe2f1] z-10"
                          style={{
                            left: `${comparisonPosition.median}%`,
                          }}
                        />
                      )}

                      <div
                        className="absolute top-0 h-full w-2 bg-[#ffc174] z-20 rounded"
                        style={{
                          left: `${Math.min(
                            98,
                            comparisonPosition.current,
                          )}%`,
                        }}
                      />
                    </div>

                    <div className="flex justify-between flex-wrap gap-2 font-caption-mono text-[10px] text-[#a08e7a]">
                      <span>Q1: {formatNumber(comparison.q25)}</span>
                      <span>Median: {formatNumber(comparison.median)}</span>
                      <span>Q3: {formatNumber(comparison.q75)}</span>
                      <span className="text-[#ffc174] font-bold">
                        Current: {formatNumber(comparison.current)}
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-[#a08e7a]">
                    Insufficient comparison values to draw the distribution
                    band.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

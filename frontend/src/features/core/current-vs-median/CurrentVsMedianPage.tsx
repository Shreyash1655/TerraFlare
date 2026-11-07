
import { useEffect, useMemo, useState } from 'react';
import { getCurrentVsMedian, getRegions } from '../../../api/core';

const months = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
];

type Region = {
  region_id: string;
  name: string;
};

type CurrentVsMedianData = {
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

function formatValue(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return value.toLocaleString('en-IN', {
    maximumFractionDigits: 1,
  });
}

function getDeviation(data: CurrentVsMedianData | null) {
  if (!data || data.current === null || data.median === null) {
    return {
      title: 'INSUFFICIENT DATA',
      description: 'Comparison values are unavailable.',
      color: 'text-[#a08e7a]',
    };
  }

  if (data.q75 !== null && data.current > data.q75) {
    return {
      title: 'ELEVATED ACTIVITY',
      description: 'Exceeds the historical 75th percentile.',
      color: 'text-[#ff938c]',
    };
  }

  if (data.q25 !== null && data.current < data.q25) {
    return {
      title: 'BELOW NORMAL',
      description: 'Below the historical 25th percentile.',
      color: 'text-[#7bd0ff]',
    };
  }

  return {
    title: 'WITHIN NORMAL RANGE',
    description: 'Within the historical interquartile range.',
    color: 'text-[#ffc174]',
  };
}

export default function CurrentVsMedianPage() {
  const [selectedMonth, setSelectedMonth] = useState(8);
  const [selectedRegion, setSelectedRegion] = useState('');

  const [regions, setRegions] = useState<Region[]>([]);
  const [comparison, setComparison] =
    useState<CurrentVsMedianData | null>(null);

  const [dataMode, setDataMode] = useState<'fixture' | 'real' | null>(null);
  const [isSynthetic, setIsSynthetic] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load available regions.
  useEffect(() => {
    let active = true;

    async function loadRegions() {
      try {
        const response = await getRegions();
        if (!active) return;

        const regionList = (response.data as any).regions ?? [];

        setRegions(regionList);

        if (regionList.length > 0) {
          setSelectedRegion(regionList[0].region_id);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load regions.',
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

  // Fetch comparison whenever region or month changes.
  useEffect(() => {
    if (!selectedRegion) return;

    let active = true;

    async function loadComparison() {
      setLoading(true);
      setError('');

      try {
        const response = await getCurrentVsMedian({
          region_id: selectedRegion,
          month: selectedMonth,
        });

        if (!active) return;

        setComparison(response.data as CurrentVsMedianData);
        setDataMode(response.meta?.data_mode ?? null);
        setIsSynthetic(response.meta?.is_synthetic ?? false);
      } catch (err) {
        if (!active) return;

        setComparison(null);
        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load historical comparison.',
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    loadComparison();

    return () => {
      active = false;
    };
  }, [selectedRegion, selectedMonth]);

  const selectedMonthName =
    months.find((month) => month.value === selectedMonth)?.label ??
    'Selected month';

  const deviation = getDeviation(comparison);

  const percentageDifference = useMemo(() => {
    if (
      comparison?.current === null ||
      comparison?.current === undefined ||
      comparison?.median === null ||
      comparison?.median === undefined ||
      comparison.median === 0
    ) {
      return null;
    }

    return (
      ((comparison.current - comparison.median) /
        comparison.median) *
      100
    );
  }, [comparison]);

  // Scale the gauge from the actual API values.
  const gauge = useMemo(() => {
    if (
      !comparison ||
      comparison.current === null ||
      comparison.q25 === null ||
      comparison.q75 === null
    ) {
      return null;
    }

    const maximum = Math.max(
      comparison.current,
      comparison.q75,
      comparison.median ?? 0,
      1,
    );

    return {
      q25: (comparison.q25 / maximum) * 100,
      q75: (comparison.q75 / maximum) * 100,
      median:
        comparison.median !== null
          ? (comparison.median / maximum) * 100
          : null,
      current: (comparison.current / maximum) * 100,
    };
  }, [comparison]);

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                BASELINE CLIMATOLOGY BENCHMARK
              </span>

              {dataMode && (
                <span className="font-caption-mono text-xs text-[#7bd0ff]">
                  / {dataMode.toUpperCase()} DATA
                </span>
              )}
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Current Month vs. Historical Median
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Compares current harmonized fire activity against the
              historical median and 25th–75th percentile range for the
              selected calendar month.
            </p>

            {isSynthetic && (
              <p className="text-xs text-[#ffc174] mt-2">
                Synthetic demonstration data — not observed fire activity.
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Region selector */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#7bd0ff] text-sm">
                travel_explore
              </span>

              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer max-w-[190px]"
              >
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

            {/* Month selector */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#ffc174] text-sm">
                calendar_month
              </span>

              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              >
                {months.map((month) => (
                  <option
                    key={month.value}
                    value={month.value}
                    className="bg-[#171b26]"
                  >
                    {month.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Partial Month Warning */}
        {comparison?.is_partial && (
          <div className="mt-4 p-2.5 rounded bg-[#f59e0b]/15 border border-[#f59e0b]/40 flex flex-wrap items-center justify-between gap-2 text-xs font-caption-mono text-[#ffc174]">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">
                info
              </span>

              <span>
                <strong>PARTIAL MONTH OBSERVATION:</strong> Current
                activity is compared using a like-for-like observation
                period.
              </span>
            </div>

            <span className="text-[#a08e7a]">
              N = {comparison.n_baseline_years} baseline years
            </span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
            {error}
            <button
              type="button"
              onClick={() => setSelectedMonth((month) => month)}
              className="ml-3 underline"
            >
              Retry by changing the month
            </button>
          </div>
        )}
      </section>

      {/* Main Gauge & Metrics */}
      <div className="w-full px-6 py-6 space-y-6">
        {loading && (
          <div className="py-3 text-center text-sm text-[#7bd0ff] font-mono">
            Loading climatology comparison...
          </div>
        )}

        {/* Metric Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Current Observed Activity
            </span>

            <div className="my-2">
              <span className="font-mono text-3xl font-bold text-[#ffc174]">
                {formatValue(comparison?.current)}
              </span>
            </div>

            <span className="font-caption-mono text-xs text-[#7bd0ff] font-bold">
              {percentageDifference === null
                ? 'Comparison unavailable'
                : `${percentageDifference >= 0 ? '+' : ''}${percentageDifference.toFixed(1)}% vs Median`}
            </span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Historical Median Baseline
            </span>

            <div className="my-2">
              <span className="font-mono text-3xl font-bold text-[#dfe2f1]">
                {formatValue(comparison?.median)}
              </span>
            </div>

            <span className="font-caption-mono text-xs text-[#d8c3ad]">
              {comparison
                ? `${comparison.n_baseline_years} baseline years`
                : 'Reference unavailable'}
            </span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Interquartile Range (IQR)
            </span>

            <div className="my-2">
              <span className="font-mono text-2xl font-bold text-[#7bd0ff]">
                [{formatValue(comparison?.q25)} – {formatValue(comparison?.q75)}]
              </span>
            </div>

            <span className="font-caption-mono text-xs text-[#d8c3ad]">
              25th to 75th Percentile
            </span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
              Deviation Status
            </span>

            <div className="my-2">
              <span className={`font-mono text-xl font-bold ${deviation.color}`}>
                {deviation.title}
              </span>
            </div>

            <span className={`font-caption-mono text-xs ${deviation.color}`}>
              {deviation.description}
            </span>
          </div>
        </div>

        {/* Visual Percentile Gauge */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">
                Climatological Range &amp; Outlier Distribution
              </h2>

              <span className="font-caption-mono text-xs text-[#a08e7a]">
                Current activity relative to the historical distribution
              </span>
            </div>

            <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
              {selectedMonthName.toUpperCase()} CLIMATOLOGY
            </span>
          </div>

          <div className="p-6 bg-[#0a0e18] rounded border border-[#262a35] flex flex-col gap-6">
            {gauge ? (
              <>
                <div className="relative w-full h-12 bg-[#171b26] rounded-lg border border-[#262a35]">
                  {/* IQR band */}
                  <div
                    className="absolute h-full bg-[#7bd0ff]/20 border-x-2 border-[#7bd0ff]/50"
                    style={{
                      left: `${gauge.q25}%`,
                      width: `${Math.max(0, gauge.q75 - gauge.q25)}%`,
                    }}
                  />

                  {/* Median */}
                  {gauge.median !== null && (
                    <div
                      className="absolute h-full w-1 bg-[#dfe2f1] z-10"
                      style={{ left: `${gauge.median}%` }}
                    />
                  )}

                  {/* Current observation */}
                  <div
                    className="absolute h-full w-2.5 bg-[#f59e0b] z-20 rounded shadow-md ring-2 ring-[#ffc174]"
                    style={{
                      left: `${Math.min(98, gauge.current)}%`,
                    }}
                  />
                </div>

                <div className="flex justify-between flex-wrap gap-3 font-caption-mono text-xs text-[#a08e7a]">
                  <span>Q1: {formatValue(comparison?.q25)}</span>

                  <span className="text-[#dfe2f1] font-bold">
                    Median: {formatValue(comparison?.median)}
                  </span>

                  <span>Q3: {formatValue(comparison?.q75)}</span>

                  <span className="text-[#ffc174] font-bold">
                    Current: {formatValue(comparison?.current)}
                  </span>
                </div>
              </>
            ) : (
              <div className="text-sm text-[#a08e7a] text-center py-8">
                The API has not provided enough values to draw the
                climatological distribution.
              </div>
            )}
          </div>
        </div>

        {/* Methodology note */}
        <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
          <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-2">
            Interpretation
          </h3>

          <p className="text-xs leading-relaxed text-[#a08e7a]">
            The median represents the central historical activity level
            for the selected month. The interquartile range contains the
            middle 50% of baseline observations. Values above the 75th
            percentile are classified as elevated relative to this
            historical distribution. This is a statistical comparison,
            not a prediction of fire behaviour or an explanation of its
            causes.
          </p>
        </div>
      </div>
    </div>
  );
}

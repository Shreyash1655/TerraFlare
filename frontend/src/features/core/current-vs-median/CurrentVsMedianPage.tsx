import { useState } from 'react';

export default function CurrentVsMedianPage() {
  const [selectedMonth, setSelectedMonth] = useState<number>(8); // August
  const isPartial = true;

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
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">24-YEAR STATISTICAL SPREAD</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Current Month vs. Historical Median
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Compares active thermal radiance against the 24-year climatological median (2000–2024) and 25th–75th interquartile range (IQR). Highlights anomalous fire surges without conflating differing sensor sensitivities.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#ffc174] text-sm">calendar_month</span>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              >
                <option className="bg-[#171b26]" value={6}>June (Early Season)</option>
                <option className="bg-[#171b26]" value={7}>July (Mid Season)</option>
                <option className="bg-[#171b26]" value={8}>August (Peak Season)</option>
                <option className="bg-[#171b26]" value={9}>September (Late Surge)</option>
                <option className="bg-[#171b26]" value={10}>October (Autumn Trail)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Partial Month Warning Banner */}
        {isPartial && (
          <div className="mt-4 p-2.5 rounded bg-[#f59e0b]/15 border border-[#f59e0b]/40 flex items-center justify-between text-xs font-caption-mono text-[#ffc174]">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">info</span>
              <span>
                <strong>PARTIAL MONTH OBSERVATION ACTIVE:</strong> Current month data is compared on a like-for-like basis (same cumulative elapsed days).
              </span>
            </div>
            <span className="text-[#a08e7a]">N = 24 Baseline Years</span>
          </div>
        )}
      </section>

      {/* Main Gauge & Metrics Grid */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Metric Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Current Observed Activity</span>
            <div className="my-2">
              <span className="font-mono text-3xl font-bold text-[#ffc174]">512.0</span>
              <span className="font-caption-mono text-xs text-[#a08e7a] ml-1.5">eq/day</span>
            </div>
            <span className="font-caption-mono text-xs text-[#7bd0ff] font-bold">+49.7% vs Median</span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Historical Median Baseline</span>
            <div className="my-2">
              <span className="font-mono text-3xl font-bold text-[#dfe2f1]">342.0</span>
              <span className="font-caption-mono text-xs text-[#a08e7a] ml-1.5">eq/day</span>
            </div>
            <span className="font-caption-mono text-xs text-[#d8c3ad]">2000–2024 Reference</span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Interquartile Range (IQR)</span>
            <div className="my-2">
              <span className="font-mono text-3xl font-bold text-[#7bd0ff]">[240 – 480]</span>
            </div>
            <span className="font-caption-mono text-xs text-[#d8c3ad]">25th to 75th Percentile</span>
          </div>

          <div className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Deviation Status</span>
            <div className="my-2">
              <span className="font-mono text-2xl font-bold text-[#ff938c]">ELEVATED SURGE</span>
            </div>
            <span className="font-caption-mono text-xs text-[#ff938c]">Exceeds 75th Percentile</span>
          </div>
        </div>

        {/* Visual Percentile Gauge */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">Climatological Range &amp; Outlier Distribution</h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">Current daily thermal output relative to historical normal range</span>
            </div>
            <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
              AUGUST CLIMATOLOGY
            </span>
          </div>

          <div className="p-6 bg-[#0a0e18] rounded border border-[#262a35] flex flex-col gap-6">
            <div className="relative w-full h-12 bg-[#171b26] rounded-lg border border-[#262a35] overflow-hidden flex items-center">
              {/* Interquartile shaded band */}
              <div
                className="absolute h-full bg-[#7bd0ff]/20 border-x-2 border-[#7bd0ff]/50"
                style={{ left: '35%', width: '35%' }}
              >
                <span className="absolute top-1 left-2 font-caption-mono text-[10px] text-[#7bd0ff] font-bold">
                  NORMAL IQR (240–480 eq)
                </span>
              </div>
              {/* Historical median line */}
              <div
                className="absolute h-full w-1 bg-[#dfe2f1] z-10 shadow"
                style={{ left: '50%' }}
              >
                <div className="absolute -top-6 -left-8 font-caption-mono text-[10px] text-[#dfe2f1] font-bold bg-[#1c1f2a] px-1.5 py-0.5 rounded border border-[#262a35]">
                  MEDIAN: 342
                </div>
              </div>
              {/* Current observation pin */}
              <div
                className="absolute h-full w-2.5 bg-[#f59e0b] z-20 rounded shadow-md ring-2 ring-[#ffc174]"
                style={{ left: '74%' }}
              >
                <div className="absolute -bottom-6 -left-10 font-caption-mono text-[10px] text-[#0B0F19] font-bold bg-[#f59e0b] px-1.5 py-0.5 rounded">
                  CURRENT: 512 (+49.7%)
                </div>
              </div>
            </div>

            <div className="flex justify-between font-caption-mono text-xs text-[#a08e7a] pt-4">
              <span>0 eq (Quiescent)</span>
              <span>240 eq (Q1 - 25th)</span>
              <span className="text-[#dfe2f1] font-bold">342 eq (Climatological Median)</span>
              <span>480 eq (Q3 - 75th)</span>
              <span className="text-[#ffc174] font-bold">700 eq (Historic Extreme)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { getCalendar, getRegions } from '../../../api/core';

const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

type CalendarDay = {
  date: string;
  harmonized_value: number | null;
  data_flag?: string;
  reason?: string;
  is_provisional?: boolean;
};
type Region = { region_id: string; name: string };

const NA = 'not available';
const fmt = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? NA : Math.round(v).toLocaleString('en-IN');
const monthDays = (y: number, m: number) => new Date(y, m + 1, 0).getDate();

function dayColor(day: CalendarDay | undefined, max: number) {
  if (!day || day.harmonized_value === null) return 'bg-[#111827] border border-dashed border-[#596273]';
  if (day.harmonized_value === 0) return 'bg-[#1c1f2a]';
  // Log scale: daily counts are strongly skewed.
  const r = Math.log1p(day.harmonized_value) / Math.log1p(Math.max(max, 1));
  if (r < 0.25) return 'bg-[#7bd0ff]/30';
  if (r < 0.5) return 'bg-[#7bd0ff]/60';
  if (r < 0.75) return 'bg-[#ffc174]/70';
  return 'bg-[#f59e0b]';
}

export default function CalendarPage() {
  const [year, setYear] = useState<number | null>(null);
  const [region, setRegion] = useState('');
  const [regions, setRegions] = useState<Region[]>([]);
  const [years, setYears] = useState<number[]>([]);
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [unit, setUnit] = useState('');
  const [limits, setLimits] = useState<string[]>([]);
  const [synthetic, setSynthetic] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    getRegions()
      .then((r) => {
        if (!active) return;
        const list = ((r.data as any).regions ?? []) as Region[];
        setRegions(list);
        setRegion(list[0]?.region_id ?? '');
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : 'Unable to load regions.'));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!region) return;
    let active = true;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const res = await getCalendar({ region_id: region, ...(year ? { year } : {}) });
        if (!active) return;
        const d = res.data as any;
        setDays(d.days ?? []);
        setUnit(d.unit ?? '');
        setLimits((res.meta as any)?.limitations ?? []);
        setSynthetic(res.meta?.is_synthetic === true);
        if (Array.isArray(d.available_years)) setYears(d.available_years);
        if (!year && d.year) setYear(Number(d.year));
      } catch (e) {
        if (active) {
          const m = (e as { error?: { message?: string } })?.error?.message;
          setError(e instanceof Error ? e.message : m ?? 'Unable to load calendar data.');
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [region, year, reloadKey]);

  const dayMap = useMemo(() => new Map(days.map((d) => [d.date, d])), [days]);
  const stats = useMemo(() => {
    const valid = days.filter((d) => d.harmonized_value !== null);
    const total = valid.reduce((s, d) => s + (d.harmonized_value ?? 0), 0);
    const peak = valid.reduce<CalendarDay | null>(
      (p, d) => (!p || (d.harmonized_value ?? 0) > (p.harmonized_value ?? 0) ? d : p), null);
    return {
      total, peak, covered: valid.length, missing: days.length - valid.length,
      provisional: days.filter((d) => d.is_provisional && d.harmonized_value !== null).length,
    };
  }, [days]);

  const y = year ?? new Date().getFullYear();
  const peakValue = stats.peak?.harmonized_value ?? 1;

  if (loading && days.length === 0 && !error) {
    return <div className="min-h-[300px] flex items-center justify-center text-[#7bd0ff] font-mono text-sm">Loading calendar data...</div>;
  }

  return (
    <div className="flex flex-col w-full pb-16">
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div className="max-w-3xl">
            <h1 className="text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Historical Burning Activity Calendar
            </h1>
            <p className="text-xs sm:text-sm text-[#d8c3ad] mt-1 leading-relaxed">
              {unit || NA}. Dashed cells are missing data (no coverage, partial edge day or suspect zero), not zero activity.
            </p>
            {synthetic && (
              <span className="mt-2 block text-xs text-[#ffc174]">Synthetic demonstration data — not observed fire activity.</span>
            )}
            {stats.provisional > 0 && (
              <span className="mt-2 block text-xs text-[#7bd0ff]">
                {stats.provisional} day(s) come from the provisional NRT stream (amber ring); not science-quality.
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 bg-[#171b26] p-1.5 rounded-lg border border-[#262a35]">
            <select value={region} onChange={(e) => setRegion(e.target.value)} aria-label="Region"
              className="bg-[#1c1f2a] px-3 py-1.5 rounded border border-[#262a35] text-xs text-[#dfe2f1]">
              {regions.map((r) => (<option key={r.region_id} value={r.region_id}>{r.name}</option>))}
            </select>
            <label className="text-[10px] text-[#a08e7a] px-1">YEAR:</label>
            <select value={y} onChange={(e) => setYear(Number(e.target.value))} aria-label="Year"
              className="bg-[#1c1f2a] px-3 py-1.5 rounded border border-[#262a35] text-xs text-[#ffc174] font-semibold">
              {(years.length ? years : [y]).map((v) => (<option key={v} value={v}>{v}</option>))}
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
            {error}
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="ml-3 underline">Retry</button>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-5">
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="text-[10px] text-[#a08e7a] uppercase">Detections (covered days)</span>
            <div className="text-2xl font-bold text-[#ffc174] mt-1">{stats.covered ? fmt(stats.total) : NA}</div>
            <span className="text-[10px] text-[#d8c3ad]">Sum over covered days only</span>
          </div>
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="text-[10px] text-[#a08e7a] uppercase">Peak covered day</span>
            <div className="text-xl font-bold text-[#dfe2f1] mt-1">{stats.peak?.date ?? NA}</div>
            <span className="text-[10px] text-[#d8c3ad]">{fmt(stats.peak?.harmonized_value)} detections</span>
          </div>
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="text-[10px] text-[#a08e7a] uppercase">Covered days</span>
            <div className="text-2xl font-bold text-[#7bd0ff] mt-1">{stats.covered}</div>
            <span className="text-[10px] text-[#d8c3ad]">Value reported (can be a true 0)</span>
          </div>
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35]">
            <span className="text-[10px] text-[#a08e7a] uppercase">Missing days</span>
            <div className="text-2xl font-bold text-[#ffddb8] mt-1">{stats.missing}</div>
            <span className="text-[10px] text-[#d8c3ad]">In coverage table, no usable value</span>
          </div>
        </div>
      </section>

      <section className="w-full px-6 py-6 space-y-6">
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5">
          <h2 className="text-base font-bold text-[#dfe2f1]">Daily NOAA-20 VIIRS activity ({y})</h2>
          <p className="text-xs text-[#a08e7a] mt-1">Colour is log-scaled to the year&apos;s peak. Days absent from the coverage table show as dashed.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-4">
            {months.map((month, mi) => {
              const n = monthDays(y, mi);
              const first = new Date(y, mi, 1).getDay();
              return (
                <div key={month} className="bg-[#171b26] p-3 rounded border border-[#262a35]">
                  <div className="flex justify-between mb-3 text-xs">
                    <span className="font-bold text-[#dfe2f1]">{month}</span>
                    <span className="text-[#a08e7a]">{n} days</span>
                  </div>
                  <div className="grid grid-cols-7 gap-1 mb-1">
                    {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((w, i) => (
                      <span key={`${w}-${i}`} className="text-center text-[9px] text-[#a08e7a]">{w}</span>
                    ))}
                  </div>
                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: first }).map((_, i) => (<div key={`e${i}`} />))}
                    {Array.from({ length: n }).map((_, di) => {
                      const date = `${y}-${String(mi + 1).padStart(2, '0')}-${String(di + 1).padStart(2, '0')}`;
                      const day = dayMap.get(date);
                      const missing = !day || day.harmonized_value === null;
                      const tip = !day
                        ? `${date} | Not in coverage table: no data`
                        : missing
                          ? `${date} | No data: ${day.reason || NA}`
                          : `${date} | ${fmt(day.harmonized_value)} detections${day.is_provisional ? ' | NRT (provisional)' : ''}`;
                      return (
                        <div key={date} title={tip}
                          className={`relative aspect-square rounded-sm ${dayColor(day, peakValue)} ${
                            !missing && day?.is_provisional ? 'ring-1 ring-[#f59e0b]' : ''
                          } hover:ring-2 hover:ring-[#7bd0ff]`}>
                          <span className="absolute inset-0 flex items-center justify-center text-[8px] text-[#dfe2f1]/80">{di + 1}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-4 mt-4 border-t border-[#262a35] text-xs text-[#a08e7a]">
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#1c1f2a] rounded-sm" />0 (covered)</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#7bd0ff]/30 rounded-sm" />low</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#7bd0ff]/60 rounded-sm" />medium</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#ffc174]/70 rounded-sm" />high</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#f59e0b] rounded-sm" />peak</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 bg-[#111827] border border-dashed border-[#596273] rounded-sm" />no data</span>
            <span className="flex items-center gap-1"><span className="w-4 h-3 rounded-sm ring-1 ring-[#f59e0b]" />NRT (provisional)</span>
          </div>
        </div>

        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5">
          <h3 className="text-base font-bold text-[#dfe2f1]">Method and limits</h3>
          <p className="text-xs text-[#a08e7a] mt-1">No multi-year baseline is computed, so there is no current-vs-median comparison.</p>
          <ul className="list-disc pl-5 mt-3 space-y-1 text-xs text-[#d8c3ad]">
            {limits.map((l) => (<li key={l}>{l}</li>))}
          </ul>
        </div>
      </section>
    </div>
  );
}
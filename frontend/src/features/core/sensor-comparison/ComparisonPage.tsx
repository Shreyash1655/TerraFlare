import { useEffect, useMemo, useState } from 'react';
import MethodDrawer from '../../../components/provenance/MethodDrawer';
import {
  getRegions,
  getHarmonizationComparison,
  getHarmonizationMethod,
  getHarmonizationCoverage,
  getFrpCalibration,
} from '../../../api/core';

type ComparisonData = Awaited<ReturnType<typeof getHarmonizationComparison>>['data'];
type MethodData = Awaited<ReturnType<typeof getHarmonizationMethod>>['data'];
type CoverageData = Awaited<ReturnType<typeof getHarmonizationCoverage>>['data'];
type FrpData = Awaited<ReturnType<typeof getFrpCalibration>>['data'];
type Region = Awaited<ReturnType<typeof getRegions>>['data']['regions'][number];
type SeriesKey = 'modis_observed' | 'viirs_observed' | 'harmonized_value';
type MetaLike = { warnings?: string[]; reliability?: string; is_synthetic?: boolean; data_mode?: string };
type Row = { period: string; vals: Record<SeriesKey, number | null>; provisional: boolean | null; missing: boolean };

const NA = 'not available';
const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined || !Number.isFinite(v)
    ? NA
    : new Intl.NumberFormat('en-IN', { maximumFractionDigits: digits }).format(v);
const pct = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? NA : `${(v * 100).toFixed(1)}%`;
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

function errText(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  const m = (err as { error?: { message?: string } } | null)?.error?.message;
  return m ?? fallback;
}

const KEYS: SeriesKey[] = ['modis_observed', 'viirs_observed', 'harmonized_value'];

function nextPeriod(p: string, g: 'day' | 'month'): string {
  if (g === 'month') {
    const [y, m] = p.split('-').map(Number);
    const d = new Date(Date.UTC(y, m, 1));
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
  }
  const d = new Date(`${p}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

const card = 'bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5';
const h2 = 'text-base font-bold text-[#dfe2f1]';
const sub = 'text-xs text-[#a08e7a] mt-1';

export default function ComparisonPage() {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [regions, setRegions] = useState<Region[]>([]);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [method, setMethod] = useState<MethodData | null>(null);
  const [coverage, setCoverage] = useState<CoverageData | null>(null);
  const [frp, setFrp] = useState<FrpData | null>(null);
  const [sideErrors, setSideErrors] = useState<string[]>([]);
  const [isMock, setIsMock] = useState(false);
  const [reliability, setReliability] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [granularity, setGranularity] = useState<'day' | 'week' | 'month'>('month');
  const [warnings, setWarnings] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await getRegions();
        if (cancelled) return;
        const list = response.data.regions ?? [];
        setRegions(list);
        setSelectedRegion((cur) =>
          list.some((r) => r.region_id === cur) ? cur : (list[0]?.region_id ?? 'global')
        );
      } catch (err) {
        if (cancelled) return;
        setError(errText(err, 'Unable to load regions.'));
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedRegion) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [c, m] = await Promise.all([
          getHarmonizationComparison({ region_id: selectedRegion, granularity }),
          getHarmonizationMethod(),
        ]);
        if (cancelled) return;
        const meta = c.meta as unknown as MetaLike | undefined;
        setComparison(c.data);
        setWarnings(meta?.warnings ?? []);
        setReliability(meta?.reliability ?? null);
        setIsMock(meta?.is_synthetic === true || meta?.data_mode === 'fixture');
        setMethod(m.data);
        // Secondary panels: a failure shows an explicit message, never fallback values.
        const errs: string[] = [];
        const [cov, fr] = await Promise.allSettled([getHarmonizationCoverage(), getFrpCalibration()]);
        if (cancelled) return;
        if (cov.status === 'fulfilled') setCoverage(cov.value.data);
        else { setCoverage(null); errs.push(`Coverage: ${errText(cov.reason, 'unavailable')}`); }
        if (fr.status === 'fulfilled') setFrp(fr.value.data);
        else { setFrp(null); errs.push(`FRP calibration: ${errText(fr.reason, 'unavailable')}`); }
        setSideErrors(errs);
      } catch (err) {
        if (cancelled) return;
        setError(errText(err, 'Unable to load harmonization comparison data.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedRegion, reloadKey, granularity]);

  const series = comparison?.series ?? [];
  const prov = comparison?.provenance;
  const diag = comparison?.diagnostics;

  const chart = useMemo(() => {
    if (series.length === 0) return null;
    const read = (p: (typeof series)[number], k: SeriesKey): number | null => {
      const v = p[k] as number | null | undefined;
      return isNum(v) ? v : null;
    };
    // Real rows, then fill absent periods (month/day) with explicit null rows.
    const real = new Map<string, Row>();
    series.forEach((p) => {
      real.set(p.period, {
        period: p.period,
        vals: {
          modis_observed: read(p, 'modis_observed'),
          viirs_observed: read(p, 'viirs_observed'),
          harmonized_value: read(p, 'harmonized_value'),
        },
        provisional: p.is_provisional ?? null,
        missing: false,
      });
    });
    const fmt = granularity === 'month' ? /^\d{4}-\d{2}$/ : /^\d{4}-\d{2}-\d{2}$/;
    const periods = series.map((p) => p.period);
    let rows: Row[] = periods.map((p) => real.get(p) as Row);
    if (granularity !== 'week' && periods.every((p) => fmt.test(p))) {
      const sorted = [...periods].sort();
      const filled: Row[] = [];
      let cur = sorted[0];
      const last = sorted[sorted.length - 1];
      let guard = 0;
      while (cur <= last && guard++ < 6000) {
        filled.push(
          real.get(cur) ?? {
            period: cur,
            vals: { modis_observed: null, viirs_observed: null, harmonized_value: null },
            provisional: null,
            missing: true,
          }
        );
        cur = nextPeriod(cur, granularity);
      }
      rows = filled;
    }

    const values: number[] = [];
    rows.forEach((r) => KEYS.forEach((k) => { const v = r.vals[k]; if (v !== null) values.push(v); }));
    const maximum = Math.max(...values, 1);
    const width = 700, height = 240, padL = 52, padR = 24, padT = 24, padB = 34;
    const x = (i: number) => padL + (i / Math.max(rows.length - 1, 1)) * (width - padL - padR);
    const y = (v: number) => height - padB - (v / maximum) * (height - padB - padT);
    // Null values break the line; they are never drawn as zero.
    const path = (k: SeriesKey) => {
      let d = '', down = false;
      rows.forEach((r, i) => {
        const v = r.vals[k];
        if (v === null) { down = false; return; }
        d += `${down ? 'L' : 'M'} ${x(i)} ${y(v)} `;
        down = true;
      });
      return d.trim();
    };
    const marks = (k: SeriesKey) =>
      rows.flatMap((r, i) => { const v = r.vals[k]; return v === null ? [] : [{ cx: x(i), cy: y(v), i }]; });

    // Shaded runs of missing periods.
    const gaps: { x1: number; x2: number; from: string; to: string }[] = [];
    let i = 0;
    while (i < rows.length) {
      if (rows[i].missing) {
        let j = i;
        while (j + 1 < rows.length && rows[j + 1].missing) j++;
        gaps.push({
          x1: x(Math.max(i - 1, 0)), x2: x(Math.min(j + 1, rows.length - 1)),
          from: rows[i].period, to: rows[j].period,
        });
        i = j + 1;
      } else i++;
    }

    // Partial periods: a VIIRS gap starts inside an otherwise present period.
    const partial = new Set<string>();
    if (granularity !== 'week') {
      (coverage?.gaps?.viirs ?? []).forEach((g) => {
        const key = granularity === 'month' ? g.start.slice(0, 7) : g.start;
        const r = rows.find((q) => q.period === key);
        if (r && !r.missing) partial.add(key);
      });
    }
    const partialMarks = rows.flatMap((r, idx) => {
      const v = r.vals.viirs_observed;
      return partial.has(r.period) && v !== null ? [{ cx: x(idx), cy: y(v), p: r.period }] : [];
    });

    const step = Math.max(1, Math.ceil(rows.length / 8));
    const xTicks = rows.flatMap((r, idx) => (idx % step === 0 ? [{ tx: x(idx), label: r.period }] : []));
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ ty: y(maximum * f), label: num(maximum * f, 0) }));
    const seam = rows.findIndex((r) => r.provisional === true);
    return {
      width, height, padL, padR, padT, padB,
      viirs: path('viirs_observed'), modis: path('modis_observed'), harm: path('harmonized_value'),
      vp: marks('viirs_observed'), mp: marks('modis_observed'),
      gaps, partialMarks, partial: [...partial], xTicks, yTicks,
      hasGaps: gaps.length > 0 || rows.some((r) => r.vals.harmonized_value === null),
      seamX: seam >= 0 ? x(seam) : null,
    };
  }, [series, granularity, coverage]);

  return (
    <div className="flex flex-col w-full pb-16">
      <section className="w-full px-6 pt-5 pb-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-2 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                Reconciliation suite
              </span>
              {isMock || prov?.is_synthetic ? (
                <span className="px-2 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-[10px] font-bold">
                  SYNTHETIC - NOT NASA DATA
                </span>
              ) : prov ? (
                <span className="px-2 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] font-caption-mono text-[10px] font-bold">
                  REAL DATA
                </span>
              ) : null}
              {prov?.processing_mode && (
                <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] font-bold">
                  PROCESSING: {prov.processing_mode}
                </span>
              )}
              <span className="font-caption-mono text-xs text-[#7bd0ff]">H3 RES 5 GRAIN</span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              MODIS vs. VIIRS Calibration &amp; Harmonization
            </h1>
            <p className="text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Hotspots are thermal-anomaly detections, not unique fires. MODIS and VIIRS counts differ in
              resolution and sensitivity and are never added together.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="bg-[#171b26] border border-[#374151] rounded px-3 py-2 text-xs text-[#dfe2f1] outline-none"
              aria-label="Select region"
            >
              {regions.map((r) => (<option key={r.region_id} value={r.region_id}>{r.name}</option>))}
            </select>
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="px-3.5 py-2 rounded bg-[#1c1f2a] hover:bg-[#262a35] text-[#dfe2f1] border border-[#374151] text-xs font-semibold"
            >
              Methodology
            </button>
            <button
              onClick={() => setReloadKey((v) => v + 1)}
              disabled={loading}
              className="px-3.5 py-2 rounded bg-[#f59e0b] text-[#0B0F19] text-xs font-bold hover:bg-[#ffb95f] disabled:opacity-50"
            >
              Refresh data
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mt-6">
          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">Correlation (raw)</p>
            <p className="text-2xl font-bold text-[#7bd0ff] mt-1">{loading ? '...' : num(diag?.correlation)}</p>
            <p className="text-[10px] text-[#a08e7a] mt-1">
              {diag?.correlation == null ? `Not computed (paired days: ${diag?.correlation_n ?? 0})` : `n=${diag?.correlation_n} paired days; includes shared seasonal cycle`}
            </p>
          </div>
          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">Correlation (deseasonalized)</p>
            <p className="text-2xl font-bold text-[#7bd0ff] mt-1">{loading ? '...' : num(diag?.correlation_deseasonalized)}</p>
            <p className="text-[10px] text-[#a08e7a] mt-1">Log counts minus 15-day running median</p>
          </div>
          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">Co-detection rate</p>
            <p className="text-2xl font-bold text-[#ffc174] mt-1">{loading ? '...' : pct(diag?.co_detection_rate)}</p>
            <p className="text-[10px] text-[#a08e7a] mt-1">
              {diag?.co_detection_rate == null ? `Not computed (detected cell-days: ${diag?.co_detection_n ?? 0})` : `Cell-day level, n=${diag?.co_detection_n}`}
            </p>
          </div>
          <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
            <p className="text-[10px] text-[#a08e7a] uppercase tracking-wider">Reliability</p>
            <p className="text-lg font-bold text-[#dfe2f1] mt-2 truncate">
              {loading ? '...' : (prov?.reliability_status ?? reliability ?? NA)}
            </p>
            <p className="text-[10px] text-[#a08e7a] mt-1">Direct observation: no conversion uncertainty</p>
          </div>
        </div>
      </section>

      <section className="w-full px-6 py-6 space-y-6">
        {error && (
          <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
            <p className="text-sm text-red-300 font-semibold">Unable to load comparison data</p>
            <p className="text-xs text-red-200 mt-1">{error}</p>
            <button onClick={() => setReloadKey((v) => v + 1)} className="mt-3 text-xs text-[#ffc174] underline">
              Try again
            </button>
          </div>
        )}

        {loading && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-10 text-center text-sm text-[#d8c3ad]">
            Loading harmonization comparison...
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="p-4 rounded-lg border border-[#ffc174]/40 bg-[#ffc174]/10 text-xs text-[#ffc174]">
              Harmonized series = NOAA-20 VIIRS observation. In the VIIRS era no MODIS conversion is applied, so the
              harmonized line coincides with the VIIRS line and has no calibration interval. MODIS is shown separately
              and never added.
            </div>

            {sideErrors.length > 0 && (
              <div className="p-3 rounded border border-red-500/30 bg-red-500/10 text-xs text-red-200">
                {sideErrors.map((e) => (<p key={e}>{e}</p>))}
              </div>
            )}

            <div className={card}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5">
                <div>
                  <h2 className={h2}>Sensor Comparison Trajectory</h2>
                  <p className={sub}>MODIS (all platforms), VIIRS (NOAA-20) and harmonized, covered days only</p>
                </div>
                <select
                  value={granularity}
                  onChange={(e) => setGranularity(e.target.value as 'day' | 'week' | 'month')}
                  className="px-2 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] text-xs font-mono"
                  aria-label="Granularity"
                >
                  <option value="day">day</option>
                  <option value="week">week</option>
                  <option value="month">month</option>
                </select>
              </div>
              {chart ? (
                <>
                  <div className="w-full overflow-x-auto">
                    <svg viewBox={`0 0 ${chart.width} ${chart.height}`} className="w-full min-w-[420px] h-64" role="img"
                      aria-label="MODIS, VIIRS and harmonized time series comparison">
                      {chart.yTicks.map((t) => (
                        <g key={t.ty}>
                          <line x1={chart.padL} x2={chart.width - chart.padR} y1={t.ty} y2={t.ty} stroke="#313540" strokeDasharray="4 4" />
                          <text x={chart.padL - 6} y={t.ty + 3} fill="#a08e7a" fontSize="9" textAnchor="end">{t.label}</text>
                        </g>
                      ))}
                      {chart.xTicks.map((t) => (
                        <text key={t.label} x={t.tx} y={chart.height - 12} fill="#a08e7a" fontSize="9" textAnchor="middle">{t.label}</text>
                      ))}
                      {chart.gaps.map((g) => (
                        <g key={`${g.from}-${g.to}`}>
                          <rect x={g.x1} y={chart.padT} width={Math.max(g.x2 - g.x1, 1)}
                            height={chart.height - chart.padB - chart.padT} fill="#f87171" opacity="0.08" />
                          <text x={(g.x1 + g.x2) / 2} y={chart.padT + 16} fill="#f87171" fontSize="9" textAnchor="middle">
                            No data: {g.from} to {g.to}
                          </text>
                        </g>
                      ))}
                      {chart.seamX !== null && (
                        <>
                          <line x1={chart.seamX} x2={chart.seamX} y1="10" y2={chart.height - chart.padB} stroke="#f87171" strokeDasharray="3 3" />
                          <text x={chart.seamX + 4} y="18" fill="#f87171" fontSize="10">NRT begins (provisional)</text>
                        </>
                      )}
                      {chart.viirs && <path d={chart.viirs} fill="none" stroke="#7bd0ff" strokeWidth="2.5" />}
                      {chart.modis && <path d={chart.modis} fill="none" stroke="#ffbcb7" strokeWidth="2.5" strokeDasharray="5 4" />}
                      {chart.harm && <path d={chart.harm} fill="none" stroke="#ffc174" strokeWidth="1.5" strokeDasharray="2 3" />}
                      {chart.vp.map((p) => (<circle key={`v${p.i}`} cx={p.cx} cy={p.cy} r="3" fill="#7bd0ff" />))}
                      {chart.mp.map((p) => (<circle key={`m${p.i}`} cx={p.cx} cy={p.cy} r="3" fill="#ffbcb7" />))}
                      {chart.partialMarks.map((p) => (
                        <circle key={`p${p.p}`} cx={p.cx} cy={p.cy} r="6" fill="none" stroke="#ffc174" strokeWidth="1.5" />
                      ))}
                    </svg>
                  </div>
                  <div className="flex flex-wrap gap-5 text-xs mt-3">
                    <span className="text-[#ffc174]">Harmonized (= NOAA-20, dotted)</span>
                    <span className="text-[#7bd0ff]">VIIRS NOAA-20</span>
                    <span className="text-[#ffbcb7]">MODIS</span>
                  </div>
                  {chart.hasGaps && (
                    <p className="text-[11px] text-[#a08e7a] mt-3">
                      Lines break where a sensor had no coverage (shaded). These periods are missing data, not zero
                      activity.
                    </p>
                  )}
                  {chart.partial.length > 0 && (
                    <p className="text-[11px] text-[#a08e7a] mt-1">
                      Ringed point: partial period ({chart.partial.join(', ')}). VIIRS coverage ends inside it, so
                      the value is not a full-period total.
                    </p>
                  )}
                  {granularity === 'week' && (
                    <p className="text-[11px] text-[#a08e7a] mt-1">
                      Week view: absent weeks are not gap-filled. Use month or day to see coverage gaps.
                    </p>
                  )}
                </>
              ) : (
                <div className="py-12 text-center text-sm text-[#a08e7a]">No comparison series is available.</div>
              )}
            </div>

            {prov && (
              <div className={`${card} text-xs text-[#d8c3ad] space-y-1`}>
                <h2 className={`${h2} mb-2`}>Provenance</h2>
                <p>Source: <span className="font-mono">{prov.data_source}</span></p>
                <p>Mode: {prov.data_mode} | Synthetic: {prov.is_synthetic ? 'YES' : 'no'} | Synthetic rows detected: {prov.synthetic_rows_detected ?? NA}</p>
                <p>Processing mode: {prov.processing_mode ?? NA} | Value types: {prov.value_types?.join(', ') || NA}</p>
                <p>Cell-day observations: {num(prov.observation_count, 0)}</p>
                <p>Date range: {prov.date_range.start ?? NA} to {prov.date_range.end ?? NA}</p>
                <p>
                  Covered days: VIIRS {num(prov.viirs_covered_days, 0)}, MODIS {num(prov.modis_covered_days, 0)}, both{' '}
                  {num(prov.covered_days, 0)} (basis: {prov.coverage_basis ?? NA})
                </p>
                <p>VIIRS reference platform: {prov.viirs_platforms?.join(', ') || NA}</p>
                <p>Reliability: {prov.reliability_status}</p>
                {warnings.length > 0 && (
                  <ul className="list-disc pl-5 mt-2 text-[#ffc174]">
                    {warnings.map((w) => (<li key={w}>{w}</li>))}
                  </ul>
                )}
              </div>
            )}

            <div className={card}>
              <h2 className={h2}>Coverage (from ingested file ranges)</h2>
              <p className={sub}>Never inferred from detection counts. Low fire activity is not missing coverage.</p>
              {coverage && coverage.years.length > 0 ? (
                <>
                  <div className="overflow-x-auto mt-3">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                          <th className="p-2">Year</th><th className="p-2 text-right">VIIRS days</th>
                          <th className="p-2 text-right">MODIS days</th><th className="p-2 text-right">Both</th>
                          <th className="p-2 text-right">VIIRS suspect-zero</th><th className="p-2 text-right">MODIS suspect-zero</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                        {coverage.years.map((y) => (
                          <tr key={y.year}>
                            <td className="p-2 font-mono text-[#7bd0ff]">{y.year}</td>
                            <td className="p-2 text-right">{y.viirs_covered}/{y.days_in_table}</td>
                            <td className="p-2 text-right">{y.modis_covered}/{y.days_in_table}</td>
                            <td className="p-2 text-right">{y.both_covered}</td>
                            <td className="p-2 text-right">{y.viirs_suspect_zero}</td>
                            <td className="p-2 text-right">{y.modis_suspect_zero}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-3 text-xs text-[#d8c3ad] space-y-1">
                    <p className="font-semibold text-[#7bd0ff]">VIIRS gaps (outside every file range)</p>
                    {(coverage.gaps.viirs ?? []).map((g) => (
                      <p key={g.start}>
                        {g.start} to {g.end} ({g.days} day{g.days === 1 ? '' : 's'})
                        {g.days === 1 ? ' - partial edge day of a file' : ' - no data, kept null'}
                      </p>
                    ))}
                    <p className="font-semibold text-[#7bd0ff] pt-2">VIIRS suspect-zero days (in range, zero detections; treated as missing)</p>
                    <p>{(coverage.suspect_zero_days.viirs ?? []).join(', ') || 'none'}</p>
                    <p className="text-[#a08e7a] pt-2">{coverage.assumption}</p>
                  </div>
                </>
              ) : (
                <p className="text-xs text-[#a08e7a] mt-3">Coverage: {NA}.</p>
              )}
            </div>

            <div className={card}>
              <h2 className={h2}>Harmonization Time-Series Records</h2>
              <p className={sub}>Values returned by the comparison API. Blank = not available, not zero.</p>
              <div className="overflow-x-auto mt-3">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                      <th className="p-3">Period</th><th className="p-3 text-right">MODIS</th>
                      <th className="p-3 text-right">VIIRS</th><th className="p-3 text-right">Harmonized</th>
                      <th className="p-3 text-right">Lower</th><th className="p-3 text-right">Upper</th>
                      <th className="p-3">Mode</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#262a35]">
                    {series.map((p, i) => (
                      <tr key={`${p.period}-${i}`} className="text-[#dfe2f1] hover:bg-[#262a35]/50">
                        <td className="p-3 font-mono text-[#7bd0ff]">{p.period}</td>
                        <td className="p-3 text-right">{num(p.modis_observed)}</td>
                        <td className="p-3 text-right">{num(p.viirs_observed)}</td>
                        <td className="p-3 text-right text-[#ffc174] font-semibold">{num(p.harmonized_value)}</td>
                        <td className="p-3 text-right">{num(p.lower)}</td>
                        <td className="p-3 text-right">{num(p.upper)}</td>
                        <td className="p-3">{p.is_provisional == null ? NA : p.is_provisional ? 'NRT (provisional)' : 'SP'}</td>
                      </tr>
                    ))}
                    {series.length === 0 && (
                      <tr><td colSpan={7} className="p-8 text-center text-[#a08e7a]">No records available.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={card}>
              <h2 className={h2}>FRP Calibration (diagnostic only)</h2>
              <p className={sub}>
                NOAA-20 FRP per MODIS-platform FRP on co-detected cell-days. Independent of count calibration; not
                applied to the harmonized series.
              </p>
              {frp && frp.models.length > 0 ? (
                <div className="overflow-x-auto mt-3">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                        <th className="p-2">Platform</th><th className="p-2">Status</th>
                        <th className="p-2 text-right">FRP ratio</th><th className="p-2 text-right">Co-detected cell-days</th>
                        <th className="p-2 text-right">Temporal rel. error</th><th className="p-2 text-right">Spatial rel. error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                      {frp.models.map((m) => (
                        <tr key={m.platform}>
                          <td className="p-2">{m.platform}</td><td className="p-2">{m.status}</td>
                          <td className="p-2 text-right">{num(m.frp_ratio, 3)}</td>
                          <td className="p-2 text-right">{num(m.n_paired_cell_days, 0)}</td>
                          <td className="p-2 text-right">{pct(m.temporal_rel_mae_monthly)}</td>
                          <td className="p-2 text-right">{pct(m.spatial_rel_mae_monthly)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-[#a08e7a] mt-3">FRP calibration: {NA}.</p>
              )}
            </div>

            <div className={card}>
              <h2 className={`${h2} mb-3`}>Calibration Method &amp; Validation</h2>
              <p className="text-sm text-[#d8c3ad] leading-relaxed">
                {method?.description ?? 'No method description is available.'}
              </p>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">Method / overlap</h3>
                  <p className="text-sm text-[#dfe2f1]">{method?.method_id ?? NA}</p>
                  <p className="text-xs text-[#a08e7a] mt-1">
                    S-NPP/NOAA-20 overlap: {diag?.overlap_period?.start ?? method?.overlap_period?.start ?? NA}
                    {' to '}
                    {diag?.overlap_period?.end ?? method?.overlap_period?.end ?? NA}
                  </p>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">Validation metrics</h3>
                  {method?.validation?.length ? (
                    <div className="space-y-2">
                      {method.validation.map((it, i) => (
                        <div key={`${it.metric}-${i}`} className="text-xs border-b border-[#313540] pb-2">
                          <div className="flex justify-between gap-3">
                            <span className="text-[#d8c3ad]">{it.metric}</span>
                            <span className="text-[#ffc174] font-mono">{num(it.value, 4)}</span>
                          </div>
                          <p className="text-[10px] text-[#a08e7a] mt-0.5">{it.baseline}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-[#a08e7a]">No validation metrics available.</p>
                  )}
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">Assumptions</h3>
                  <ul className="space-y-2">
                    {(method?.assumptions ?? []).map((it, i) => (
                      <li key={i} className="text-xs text-[#d8c3ad] list-disc ml-4">{it}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#7bd0ff] uppercase mb-2">Limitations</h3>
                  <ul className="space-y-2">
                    {(method?.limitations ?? []).map((it, i) => (
                      <li key={i} className="text-xs text-[#d8c3ad] list-disc ml-4">{it}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      <MethodDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
    </div>
  );
}
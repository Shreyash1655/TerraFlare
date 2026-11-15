import { useEffect, useMemo, useState } from 'react';
import { getQuality, getProvenance } from '../../../api/advanced';
import { getHarmonizationCoverage } from '../../../api/core';
import type { QualityData, ProvenanceData } from '../../../api/types/advanced';

type CoverageData = Awaited<ReturnType<typeof getHarmonizationCoverage>>['data'];
type Gap = { start: string; end: string; days: number };
type Row = Record<string, unknown>;

const NA = 'not available';
const num = (v: unknown) =>
  typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : NA;

function errText(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  return (err as { error?: { message?: string } } | null)?.error?.message ?? fallback;
}

const card = 'bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5';
const h3 = 'text-base font-bold text-[#dfe2f1]';
const sub = 'text-xs text-[#a08e7a] mt-1 leading-relaxed';

export default function QualityPage() {
  const [quality, setQuality] = useState<QualityData | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceData | null>(null);
  const [coverage, setCoverage] = useState<CoverageData | null>(null);
  const [mode, setMode] = useState<{ synthetic: boolean; label: string } | null>(null);
  const [windowText, setWindowText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sideErrors, setSideErrors] = useState<string[]>([]);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [q, p] = await Promise.all([getQuality(), getProvenance()]);
        if (cancelled) return;
        setQuality(q.data);
        setProvenance(p.data);
        setMode({ synthetic: q.meta.is_synthetic === true, label: String(q.meta.data_mode ?? '') });
        const params = (q.meta as unknown as { parameters?: Record<string, unknown> }).parameters;
        setWindowText(params?.start && params?.end ? `${params.start} to ${params.end}` : null);
        const errs: string[] = [];
        try {
          const c = await getHarmonizationCoverage();
          if (!cancelled) setCoverage(c.data);
        } catch (e) {
          setCoverage(null);
          errs.push(`Coverage: ${errText(e, 'unavailable')}`);
        }
        if (!cancelled) setSideErrors(errs);
      } catch (err) {
        if (!cancelled) setError(errText(err, 'Unable to load quality information.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [reloadKey]);

  const q = quality as unknown as {
    sensor_contribution?: Row[];
    confidence_normalised?: Row[];
    uncertainty_summary?: { interval_level?: number | null };
  } | null;

  // Raw counts per sensor + platform, summed over months. Never combined across sensors.
  const counts = useMemo(() => {
    const m = new Map<string, number>();
    (q?.sensor_contribution ?? []).forEach((r) => {
      const c = typeof r.count === 'number' ? r.count : null;
      if (c === null) return;
      const k = `${r.sensor_family}|${r.platform ?? 'unknown'}`;
      m.set(k, (m.get(k) ?? 0) + c);
    });
    return [...m.entries()].map(([k, v]) => {
      const [sensor, platform] = k.split('|');
      return { sensor, platform, count: v };
    }).sort((a, b) => a.sensor.localeCompare(b.sensor) || b.count - a.count);
  }, [q]);

  // Normalised confidence class, shares computed within one sensor only.
  const conf = useMemo(() => {
    const by = new Map<string, { cls: string; count: number }[]>();
    (q?.confidence_normalised ?? []).forEach((r) => {
      const s = String(r.sensor_family ?? 'unknown');
      const c = typeof r.count === 'number' ? r.count : 0;
      by.set(s, [...(by.get(s) ?? []), { cls: String(r.confidence_class ?? 'unknown'), count: c }]);
    });
    return [...by.entries()].map(([sensor, items]) => {
      const total = items.reduce((a, b) => a + b.count, 0);
      return { sensor, total, items: items.sort((a, b) => b.count - a.count) };
    });
  }, [q]);

  const cov = useMemo(() => {
    if (!coverage) return null;
    const years = coverage.years ?? [];
    const viirs = years.reduce((s, y) => s + y.viirs_covered, 0);
    const modis = years.reduce((s, y) => s + y.modis_covered, 0);
    const days = years.reduce((s, y) => s + y.days_in_table, 0);
    const g = (coverage as unknown as { gaps?: { viirs?: Gap[]; modis?: Gap[] } }).gaps ?? {};
    const split = (a: Gap[] = []) => ({ long: a.filter((x) => x.days > 1), edge: a.filter((x) => x.days === 1) });
    return { years, viirs, modis, days, v: split(g.viirs), m: split(g.modis) };
  }, [coverage]);

  const intervalLevel = q?.uncertainty_summary?.interval_level ?? null;

  return (
    <div className="flex flex-col w-full pb-16">
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-wrap items-center gap-2">
          {loading ? (
            <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] text-[10px] font-bold">LOADING</span>
          ) : error ? (
            <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-bold">API ERROR</span>
          ) : mode?.synthetic ? (
            <span className="px-2 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] text-[10px] font-bold">SYNTHETIC - NOT NASA DATA</span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] text-[10px] font-bold">REAL DATA</span>
          )}
        </div>
        <h1 className="text-2xl lg:text-3xl font-bold text-[#dfe2f1] mt-2 tracking-tight">Data Quality &amp; Trust</h1>
        <p className="text-sm text-[#d8c3ad] mt-1 max-w-3xl leading-relaxed">
          Can you rely on what the dashboard shows? This page answers three questions: did the satellites actually
          cover each day, how confident is each detection, and where did the data come from.
        </p>
      </section>

      <div className="w-full px-6 py-6 space-y-6">
        {loading && <div className={`${card} text-center text-sm text-[#7bd0ff]`}>Loading quality information...</div>}

        {error && !loading && (
          <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
            <p className="text-sm text-red-300 font-semibold">Unable to load quality information</p>
            <p className="text-xs text-red-200 mt-1">{error}</p>
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="mt-3 text-xs text-[#ffc174] underline">
              Try again
            </button>
          </div>
        )}

        {sideErrors.length > 0 && (
          <div className="p-3 rounded border border-red-500/30 bg-red-500/10 text-xs text-red-200">
            {sideErrors.map((e) => (<p key={e}>{e}</p>))}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
                <p className="text-[10px] uppercase text-[#a08e7a]">VIIRS days covered</p>
                <p className="text-2xl font-bold text-[#7bd0ff] mt-1">{cov ? `${num(cov.viirs)} / ${num(cov.days)}` : NA}</p>
                <p className="text-[10px] text-[#d8c3ad] mt-1">Days inside an ingested VIIRS file</p>
              </div>
              <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
                <p className="text-[10px] uppercase text-[#a08e7a]">MODIS days covered</p>
                <p className="text-2xl font-bold text-[#ffbcb7] mt-1">{cov ? `${num(cov.modis)} / ${num(cov.days)}` : NA}</p>
                <p className="text-[10px] text-[#d8c3ad] mt-1">Days inside an ingested MODIS file</p>
              </div>
              <div className="p-4 rounded bg-[#171b26] border border-[#262a35]">
                <p className="text-[10px] uppercase text-[#a08e7a]">Largest VIIRS gap</p>
                <p className="text-2xl font-bold text-[#ffc174] mt-1">
                  {cov && cov.v.long.length ? `${Math.max(...cov.v.long.map((g) => g.days))} days` : cov ? 'none' : NA}
                </p>
                <p className="text-[10px] text-[#d8c3ad] mt-1">Missing days are never counted as zero fire</p>
              </div>
            </div>

            {/* Coverage */}
            <div className={card}>
              <h3 className={h3}>Did the satellites cover each day?</h3>
              <p className={sub}>
                Coverage comes from the date range of each ingested file. It is never guessed from the number of
                detections: a quiet day with no fires still counts as covered.
              </p>
              {cov ? (
                <>
                  <div className="overflow-x-auto mt-3">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                          <th className="p-2">Year</th>
                          <th className="p-2 text-right">VIIRS days</th>
                          <th className="p-2 text-right">MODIS days</th>
                          <th className="p-2 text-right">Suspect zero (VIIRS)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                        {cov.years.map((y) => (
                          <tr key={y.year}>
                            <td className="p-2 font-mono text-[#7bd0ff]">{y.year}</td>
                            <td className="p-2 text-right">{y.viirs_covered}/{y.days_in_table}</td>
                            <td className="p-2 text-right">{y.modis_covered}/{y.days_in_table}</td>
                            <td className="p-2 text-right">{y.viirs_suspect_zero}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-4 space-y-1 text-xs text-[#d8c3ad]">
                    <p className="font-semibold text-[#7bd0ff]">Periods with no VIIRS data</p>
                    {cov.v.long.length === 0 && <p>None.</p>}
                    {cov.v.long.map((g) => (
                      <p key={g.start}>{g.start} to {g.end} ({g.days} days): no file covers this period, so values stay blank.</p>
                    ))}
                    <p className="font-semibold text-[#ffbcb7] pt-2">Periods with no MODIS data</p>
                    {cov.m.long.length === 0 && <p>None.</p>}
                    {cov.m.long.map((g) => (
                      <p key={g.start}>{g.start} to {g.end} ({g.days} days).</p>
                    ))}
                    {(cov.v.edge.length > 0 || cov.m.edge.length > 0) && (
                      <p className="text-[#a08e7a] pt-2">
                        Single partial days at the edge of a file are also treated as missing:{' '}
                        {[...cov.v.edge, ...cov.m.edge].map((g) => g.start).join(', ')}.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-xs text-[#a08e7a] mt-3">Coverage: {NA}.</p>
              )}
            </div>

            {/* Confidence + counts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className={card}>
                <h3 className={h3}>How confident is each detection?</h3>
                <p className={sub}>
                  Each sensor grades its own detections. Shares are within one sensor only; the two sensors&apos;
                  grades are not directly comparable.{windowText ? ` Window: ${windowText}.` : ''}
                </p>
                {conf.length === 0 ? (
                  <p className="text-xs text-[#a08e7a] mt-4">No confidence data for this window.</p>
                ) : (
                  <div className="mt-4 space-y-5">
                    {conf.map((s) => (
                      <div key={s.sensor}>
                        <p className="text-xs font-bold text-[#ffc174] mb-2">{s.sensor} ({num(s.total)} detections)</p>
                        <div className="space-y-2">
                          {s.items.map((it) => {
                            const pct = s.total > 0 ? (it.count / s.total) * 100 : 0;
                            return (
                              <div key={it.cls}>
                                <div className="flex justify-between text-xs text-[#dfe2f1] mb-1">
                                  <span className="capitalize">{it.cls}</span>
                                  <span className="text-[#7bd0ff]">{pct.toFixed(1)}%</span>
                                </div>
                                <div className="h-2 bg-[#0a0e18] rounded-full overflow-hidden">
                                  <div className="h-full bg-[#7bd0ff]" style={{ width: `${pct}%` }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className={card}>
                <h3 className={h3}>Detections by sensor</h3>
                <p className={sub}>
                  Raw counts per sensor and satellite for the same window. Sensors are never added together.
                </p>
                {counts.length === 0 ? (
                  <p className="text-xs text-[#a08e7a] mt-4">No detections in this window.</p>
                ) : (
                  <table className="w-full text-left text-xs mt-3">
                    <thead>
                      <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                        <th className="p-2">Sensor</th><th className="p-2">Satellite</th><th className="p-2 text-right">Detections</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                      {counts.map((c) => (
                        <tr key={`${c.sensor}-${c.platform}`}>
                          <td className="p-2 text-[#ffc174] font-semibold">{c.sensor}</td>
                          <td className="p-2">{c.platform}</td>
                          <td className="p-2 text-right font-mono">{num(c.count)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Uncertainty */}
            <div className={card}>
              <h3 className={h3}>How uncertain are the numbers?</h3>
              <p className="text-sm text-[#d8c3ad] mt-2 leading-relaxed">
                {intervalLevel === null || intervalLevel === undefined
                  ? 'The harmonized series is the NOAA-20 VIIRS observation itself, with no MODIS conversion, so no calibration interval applies. Counts are exact detection counts, not estimates. They still describe thermal anomalies, not unique fires.'
                  : `The data carry a ${(intervalLevel <= 1 ? intervalLevel * 100 : intervalLevel).toFixed(0)}% calibration interval. This describes the conversion method, not the chance that any single detection is correct.`}
              </p>
            </div>

            {/* Provenance */}
            <div className={card}>
              <h3 className={h3}>Where did the data come from?</h3>
              <p className={sub}>Source files recorded when the data was loaded.</p>
              {!provenance || provenance.sources.length === 0 ? (
                <p className="text-xs text-[#a08e7a] mt-3">No source records are available.</p>
              ) : (
                <div className="overflow-x-auto mt-3">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                        <th className="p-2">File</th><th className="p-2">Version</th>
                        <th className="p-2 text-right">Rows</th><th className="p-2">Loaded</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                      {provenance.sources.map((s, i) => (
                        <tr key={`${s.source_id}-${i}`} title={s.sha256 ? `SHA-256: ${s.sha256}` : undefined}>
                          <td className="p-2 font-mono">{s.file_name || s.source_id || NA}</td>
                          <td className="p-2">{s.product_version || NA}</td>
                          <td className="p-2 text-right font-mono">{num(s.rows_in)}</td>
                          <td className="p-2">{s.ingested_at ? String(s.ingested_at).slice(0, 10) : NA}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <details className="bg-[#171b26] border border-[#262a35] rounded-lg p-4">
              <summary className="cursor-pointer text-sm font-bold text-[#dfe2f1]">How the data is processed</summary>
              <ol className="list-decimal pl-5 mt-3 space-y-1 text-xs text-[#d8c3ad] leading-relaxed">
                <li>NASA FIRMS files (MODIS and VIIRS) are loaded and checked for valid dates and coordinates.</li>
                <li>Detections are placed on a common hexagonal grid (H3 resolution 5) per day.</li>
                <li>Near-real-time (NRT) data is kept separate from standard-processing (SP) history and is labelled provisional.</li>
                <li>Results are served by the API. Days with no coverage stay blank rather than zero.</li>
              </ol>
            </details>
          </>
        )}
      </div>
    </div>
  );
}
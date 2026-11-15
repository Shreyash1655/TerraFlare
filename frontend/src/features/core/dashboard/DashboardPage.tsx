import { useEffect, useMemo, useState } from 'react';
import {
  getRegions,
  getHotspots,
  getHotspotCells,
  getHarmonizationComparison,
  getHarmonizationCoverage,
} from '../../../api/core';

type Region = { region_id: string; name: string };
type HotspotsData = Awaited<ReturnType<typeof getHotspots>>['data'];
type CellsData = Awaited<ReturnType<typeof getHotspotCells>>['data'];
type ComparisonData = Awaited<ReturnType<typeof getHarmonizationComparison>>['data'];
type CoverageData = Awaited<ReturnType<typeof getHarmonizationCoverage>>['data'];
type View = 'cells' | 'raw';
type Row = { period: string; v: number | null; m: number | null; prov: boolean; missing: boolean };

const NA = 'n/a';
const MAX_MISSING = 14; // assumption: more uncovered days than this = incomplete year
const num = (v: number | null | undefined, d = 0) =>
  v === null || v === undefined || !Number.isFinite(v)
    ? NA
    : v.toLocaleString('en-IN', { maximumFractionDigits: d });
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

function errText(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  return (err as { error?: { message?: string } } | null)?.error?.message ?? fallback;
}

function nextMonth(p: string): string {
  const [y, m] = p.split('-').map(Number);
  const d = new Date(Date.UTC(y, m, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

const card = 'min-w-0 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-4';
const h2 = 'text-sm font-bold text-[#dfe2f1]';

function Stat({ label, value, note, accent }: { label: string; value: string; note: string; accent: string }) {
  return (
    <div className="min-w-0 p-3 rounded-lg bg-[#171b26] border border-[#262a35]">
      <p className="text-[10px] uppercase tracking-wider text-[#a08e7a] truncate">{label}</p>
      <p className={`text-xl font-bold mt-0.5 truncate ${accent}`}>{value}</p>
      <p className="text-[10px] text-[#a08e7a] mt-0.5 leading-snug">{note}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [region, setRegion] = useState('');
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [coverage, setCoverage] = useState<CoverageData | null>(null);
  const [cells, setCells] = useState<CellsData | null>(null);
  const [hotspots, setHotspots] = useState<HotspotsData | null>(null);

  const [year, setYear] = useState('');
  const [view, setView] = useState<View>('cells');
  const [h3Res, setH3Res] = useState(5);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);
  const [shown, setShown] = useState(15);

  const [loading, setLoading] = useState(true);
  const [geoLoading, setGeoLoading] = useState(false);
  const [error, setError] = useState('');
  const [geoError, setGeoError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const r = await getRegions();
        if (!active) return;
        const list = ((r.data as { regions?: Region[] }).regions ?? []) as Region[];
        setRegions(list);
        const id = list[0]?.region_id ?? 'global';
        setRegion(id);
        const [c, cov] = await Promise.all([
          getHarmonizationComparison({ region_id: id, granularity: 'month' }),
          getHarmonizationCoverage(),
        ]);
        if (!active) return;
        setComparison(c.data);
        setCoverage(cov.data);
        const years = [...(cov.data.years ?? [])].sort((a, b) => b.year - a.year);
        const complete = years.find((y) => y.viirs_covered >= y.days_in_table - MAX_MISSING);
        setYear((cur) => cur || String((complete ?? years[0])?.year ?? 'all'));
      } catch (e) {
        if (active) setError(errText(e, 'Unable to load dashboard data.'));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [reloadKey]);

  useEffect(() => {
    if (!region || !year) return;
    let active = true;
    (async () => {
      setGeoLoading(true);
      setGeoError('');
      setShown(15);
      const range = year === 'all' ? {} : { start: `${year}-01-01`, end: `${year}-12-31` };
      const sensors = [showModis && 'MODIS', showViirs && 'VIIRS'].filter(Boolean).join(',');
      try {
        const [c, h] = await Promise.all([
          getHotspotCells({ region_id: region, h3_res: h3Res, ...range }),
          view === 'raw' && sensors
            ? getHotspots({ region_id: region, sensors, limit: 500, ...range })
            : Promise.resolve(null),
        ]);
        if (!active) return;
        setCells(c.data);
        setHotspots(h ? h.data : null);
      } catch (e) {
        if (active) setGeoError(errText(e, 'Unable to load cell data.'));
      } finally {
        if (active) setGeoLoading(false);
      }
    })();
    return () => { active = false; };
  }, [region, year, h3Res, view, showModis, showViirs, reloadKey]);

  const series = comparison?.series ?? [];
  const prov = comparison?.provenance;
  const diag = comparison?.diagnostics;

  const annual = useMemo(() => {
    const byYear = new Map<number, { v: number | null; m: number | null }>();
    series.forEach((p) => {
      const y = Number(String(p.period).slice(0, 4));
      if (!Number.isFinite(y)) return;
      const cur = byYear.get(y) ?? { v: null, m: null };
      if (isNum(p.viirs_observed)) cur.v = (cur.v ?? 0) + p.viirs_observed;
      if (isNum(p.modis_observed)) cur.m = (cur.m ?? 0) + p.modis_observed;
      byYear.set(y, cur);
    });
    return (coverage?.years ?? [])
      .map((c) => {
        const t = byYear.get(c.year) ?? { v: null, m: null };
        return {
          year: c.year, v: t.v, m: t.m, vCov: c.viirs_covered, mCov: c.modis_covered, days: c.days_in_table,
          vInc: c.viirs_covered < c.days_in_table - MAX_MISSING,
          mInc: c.modis_covered < c.days_in_table - MAX_MISSING,
        };
      })
      .sort((a, b) => a.year - b.year);
  }, [series, coverage]);

  const selected = useMemo(() => {
    const rows = year === 'all' ? annual : annual.filter((a) => String(a.year) === year);
    const sum = (k: 'v' | 'm') => {
      const vals = rows.map((r) => r[k]).filter(isNum);
      return vals.length ? vals.reduce((a, b) => a + b, 0) : null;
    };
    return {
      v: sum('v'), m: sum('m'),
      vCov: rows.reduce((s, r) => s + r.vCov, 0),
      mCov: rows.reduce((s, r) => s + r.mCov, 0),
      days: rows.reduce((s, r) => s + r.days, 0),
      vInc: rows.some((r) => r.vInc), mInc: rows.some((r) => r.mInc),
    };
  }, [annual, year]);

  const chart = useMemo(() => {
    if (series.length === 0) return null;
    const real = new Map<string, Row>();
    series.forEach((p) =>
      real.set(p.period, {
        period: p.period,
        v: isNum(p.viirs_observed) ? p.viirs_observed : null,
        m: isNum(p.modis_observed) ? p.modis_observed : null,
        prov: p.is_provisional === true,
        missing: false,
      }),
    );
    const sorted = [...real.keys()].sort();
    const rows: Row[] = [];
    let cur = sorted[0];
    let guard = 0;
    while (cur <= sorted[sorted.length - 1] && guard++ < 600) {
      rows.push(real.get(cur) ?? { period: cur, v: null, m: null, prov: false, missing: true });
      cur = nextMonth(cur);
    }
    const w = 700, h = 190, padL = 48, padR = 10, padT = 10, padB = 24;
    const max = Math.max(1, ...rows.flatMap((r) => [r.v, r.m]).filter(isNum));
    const x = (i: number) => padL + (i / Math.max(rows.length - 1, 1)) * (w - padL - padR);
    const y = (v: number) => h - padB - (v / max) * (h - padB - padT);
    const path = (k: 'v' | 'm') => {
      let d = '', down = false;
      rows.forEach((r, i) => {
        const val = r[k];
        if (val === null) { down = false; return; }
        d += `${down ? 'L' : 'M'} ${x(i)} ${y(val)} `;
        down = true;
      });
      return d.trim();
    };
    const gaps: { x1: number; x2: number; label: string }[] = [];
    let i = 0;
    while (i < rows.length) {
      if (rows[i].missing) {
        let j = i;
        while (j + 1 < rows.length && rows[j + 1].missing) j++;
        gaps.push({
          x1: x(Math.max(i - 1, 0)), x2: x(Math.min(j + 1, rows.length - 1)),
          label: `No data ${rows[i].period} to ${rows[j].period}`,
        });
        i = j + 1;
      } else i++;
    }
    const step = Math.max(1, Math.ceil(rows.length / 7));
    const seam = rows.findIndex((r) => r.prov);
    return {
      w, h, padL, padB, padT, padR, viirs: path('v'), modis: path('m'), gaps,
      xTicks: rows.flatMap((r, idx) => (idx % step === 0 ? [{ tx: x(idx), label: r.period }] : [])),
      yTicks: [0, 0.5, 1].map((f) => ({ ty: y(max * f), label: num(max * f) })),
      seamX: seam >= 0 ? x(seam) : null,
    };
  }, [series]);

  const cellList = cells?.cells ?? [];
  const features = (hotspots?.features ?? []).filter((f) => {
    const s = f.properties.sensor_family;
    return !((s === 'MODIS' && !showModis) || (s === 'VIIRS' && !showViirs));
  });
  const geoMeta = hotspots as unknown as { total_matching?: number; truncated?: boolean } | null;
  const regionName = regions.find((r) => r.region_id === region)?.name ?? NA;
  const yearLabel = year === 'all' ? 'all years' : year;
  const listLen = view === 'cells' ? cellList.length : features.length;

  return (
    <div className="flex flex-col w-full min-w-0 max-w-full overflow-x-hidden pb-10">
      <section className="px-5 pt-4 pb-4 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {prov?.is_synthetic ? (
                <span className="px-2 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] text-[10px] font-bold">SYNTHETIC</span>
              ) : prov ? (
                <span className="px-2 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] text-[10px] font-bold">REAL DATA</span>
              ) : null}
              {prov?.processing_mode && (
                <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] text-[10px] font-bold">{prov.processing_mode}</span>
              )}
              <span className="text-xs text-[#a08e7a]">{regionName}</span>
            </div>
            <h1 className="text-xl font-bold text-[#dfe2f1] mt-1">Fire Activity Overview</h1>
            <p className="text-xs text-[#a08e7a] mt-0.5">Satellite heat detections by VIIRS and MODIS. A detection is a thermal anomaly, not one fire.</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={year}
              onChange={(e) => setYear(e.target.value)}
              aria-label="Period"
              className="bg-[#171b26] border border-[#374151] rounded px-3 py-1.5 text-xs text-[#ffc174] font-semibold"
            >
              {[...annual].reverse().map((a) => (
                <option key={a.year} value={String(a.year)}>{a.year}{a.vInc ? ' (incomplete)' : ''}</option>
              ))}
              <option value="all">All years</option>
            </select>
            <button type="button" onClick={() => setReloadKey((k) => k + 1)}
              className="px-3 py-1.5 rounded bg-[#1c1f2a] border border-[#374151] text-xs text-[#dfe2f1] hover:bg-[#262a35]">
              Refresh
            </button>
          </div>
        </div>
      </section>

      <div className="px-5 py-4 space-y-4 min-w-0">
        {error && (
          <div className="p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-200">
            {error}
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="ml-3 text-[#ffc174] underline">Try again</button>
          </div>
        )}
        {loading && <div className={`${card} text-center text-sm text-[#7bd0ff]`}>Loading...</div>}

        {!loading && !error && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Stat label={`VIIRS, ${yearLabel}`} value={num(selected.v)} accent="text-[#7bd0ff]"
                note={`NOAA-20 · ${num(selected.vCov)}/${num(selected.days)} days covered${selected.vInc ? ' · partial' : ''}`} />
              <Stat label={`MODIS, ${yearLabel}`} value={num(selected.m)} accent="text-[#ffbcb7]"
                note={`Terra + Aqua · ${num(selected.mCov)}/${num(selected.days)} days covered${selected.mInc ? ' · partial' : ''}`} />
              <Stat label="Both sensors, same cell-day"
                value={diag?.co_detection_rate == null ? NA : `${(diag.co_detection_rate * 100).toFixed(1)}%`}
                accent="text-[#ffc174]" note={`n = ${num(diag?.co_detection_n)} cell-days`} />
              <Stat label="Latest data" value={prov?.date_range?.end ?? NA} accent="text-[#dfe2f1]"
                note="Recent days are provisional (NRT)" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className={`${card} lg:col-span-2`}>
                <h2 className={h2}>Detections by month</h2>
                <p className="text-[11px] text-[#a08e7a] mt-0.5">Red area = no satellite file covers these dates (missing, not quiet).</p>
                {chart ? (
                  <>
                    <svg viewBox={`0 0 ${chart.w} ${chart.h}`} className="w-full h-48 mt-2" role="img" aria-label="Monthly detections">
                      {chart.yTicks.map((t) => (
                        <g key={t.ty}>
                          <line x1={chart.padL} x2={chart.w - chart.padR} y1={t.ty} y2={t.ty} stroke="#313540" strokeDasharray="4 4" />
                          <text x={chart.padL - 6} y={t.ty + 3} fill="#a08e7a" fontSize="9" textAnchor="end">{t.label}</text>
                        </g>
                      ))}
                      {chart.xTicks.map((t) => (
                        <text key={t.label} x={t.tx} y={chart.h - 8} fill="#a08e7a" fontSize="9" textAnchor="middle">{t.label}</text>
                      ))}
                      {chart.gaps.map((g) => (
                        <g key={g.label}>
                          <rect x={g.x1} y={chart.padT} width={Math.max(g.x2 - g.x1, 1)}
                            height={chart.h - chart.padB - chart.padT} fill="#f87171" opacity="0.12" />
                          <text x={(g.x1 + g.x2) / 2} y={chart.padT + 12} fill="#f87171" fontSize="9" textAnchor="middle">{g.label}</text>
                        </g>
                      ))}
                      {chart.seamX !== null && (
                        <>
                          <line x1={chart.seamX} x2={chart.seamX} y1={chart.padT} y2={chart.h - chart.padB} stroke="#f87171" strokeDasharray="3 3" />
                          <text x={chart.seamX + 4} y={chart.padT + 26} fill="#f87171" fontSize="9">NRT begins</text>
                        </>
                      )}
                      {chart.viirs && <path d={chart.viirs} fill="none" stroke="#7bd0ff" strokeWidth="2" />}
                      {chart.modis && <path d={chart.modis} fill="none" stroke="#ffbcb7" strokeWidth="2" strokeDasharray="5 4" />}
                    </svg>
                    <div className="flex flex-wrap gap-4 text-[11px] mt-1">
                      <span className="text-[#7bd0ff]">— VIIRS (NOAA-20)</span>
                      <span className="text-[#ffbcb7]">- - MODIS</span>
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-[#a08e7a] mt-3">No monthly series available.</p>
                )}
              </div>

              <div className={card}>
                <h2 className={h2}>By year</h2>
                <p className="text-[11px] text-[#a08e7a] mt-0.5">Sensors are listed side by side, never added.</p>
                <table className="w-full text-xs mt-2">
                  <thead>
                    <tr className="text-[#a08e7a] uppercase text-[10px]">
                      <th className="py-1 text-left">Year</th>
                      <th className="py-1 text-right text-[#7bd0ff]">VIIRS</th>
                      <th className="py-1 text-right text-[#ffbcb7]">MODIS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                    {annual.map((a) => (
                      <tr key={a.year} className={String(a.year) === year ? 'bg-[#262a35]/60' : ''}>
                        <td className="py-1.5 font-mono">
                          {a.year}{(a.vInc || a.mInc) && <span className="text-[#ffc174]" title="Incomplete coverage"> *</span>}
                        </td>
                        <td className="py-1.5 text-right">{num(a.v)}</td>
                        <td className="py-1.5 text-right">{num(a.m)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-[10px] text-[#a08e7a] mt-2">* part of the year has no coverage, so the total is partial.</p>
              </div>
            </div>

            <div className={card}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className={h2}>
                  {view === 'cells' ? `Map cells (H3 res ${h3Res}), ${yearLabel}` : `Individual detections, ${yearLabel}`}
                </h2>
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  {(['cells', 'raw'] as View[]).map((v) => (
                    <button key={v} type="button" onClick={() => setView(v)}
                      className={`px-2.5 py-1 rounded font-semibold ${view === v ? 'bg-[#f59e0b] text-[#0B0F19]' : 'bg-[#171b26] text-[#dfe2f1] hover:bg-[#262a35]'}`}>
                      {v === 'cells' ? 'Cells' : 'Raw'}
                    </button>
                  ))}
                  {view === 'cells' ? (
                    <span className="flex items-center gap-1 text-[#a08e7a]">
                      Res
                      {[4, 5, 6, 7].map((r) => (
                        <button key={r} type="button" onClick={() => setH3Res(r)}
                          className={`px-1.5 py-0.5 rounded font-bold ${h3Res === r ? 'bg-[#00a6e0] text-[#00374d]' : 'hover:text-[#dfe2f1]'}`}>
                          {r}
                        </button>
                      ))}
                    </span>
                  ) : (
                    <>
                      <label className="flex items-center gap-1 text-[#ffbcb7]">
                        <input type="checkbox" checked={showModis} onChange={(e) => setShowModis(e.target.checked)} /> MODIS
                      </label>
                      <label className="flex items-center gap-1 text-[#7bd0ff]">
                        <input type="checkbox" checked={showViirs} onChange={(e) => setShowViirs(e.target.checked)} /> VIIRS
                      </label>
                    </>
                  )}
                </div>
              </div>

              {geoError && <p className="text-xs text-red-300 mt-2">{geoError}</p>}
              {geoLoading ? (
                <p className="text-sm text-[#7bd0ff] py-6 text-center">Loading...</p>
              ) : (
                <div className="overflow-x-auto mt-2 rounded border border-[#262a35]">
                  {view === 'cells' ? (
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#0a0e18] text-[#a08e7a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">H3 cell</th>
                          <th className="p-2 text-right text-[#ffbcb7]">MODIS</th>
                          <th className="p-2 text-right text-[#7bd0ff]">VIIRS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                        {cellList.slice(0, shown).map((c) => (
                          <tr key={c.h3_cell} className="hover:bg-[#171b26]">
                            <td className="p-2 font-mono text-[#ffc174]">{c.h3_cell}</td>
                            <td className="p-2 text-right">{num(c.modis_observed)}</td>
                            <td className="p-2 text-right">{num(c.viirs_observed)}</td>
                          </tr>
                        ))}
                        {cellList.length === 0 && (
                          <tr><td colSpan={3} className="p-5 text-center text-[#a08e7a]">No cells for this period.</td></tr>
                        )}
                      </tbody>
                    </table>
                  ) : (
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#0a0e18] text-[#a08e7a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Time (UTC)</th><th className="p-2">Sensor</th><th className="p-2">Satellite</th>
                          <th className="p-2">Location</th><th className="p-2 text-right">FRP (MW)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#262a35] text-[#dfe2f1]">
                        {features.slice(0, shown).map((f, i) => (
                          <tr key={f.properties.obs_id ?? i} className="hover:bg-[#171b26]">
                            <td className="p-2 font-mono">{f.properties.acq_datetime_utc}</td>
                            <td className={`p-2 font-bold ${f.properties.sensor_family === 'MODIS' ? 'text-[#ffbcb7]' : 'text-[#7bd0ff]'}`}>{f.properties.sensor_family}</td>
                            <td className="p-2">{f.properties.platform ?? NA}</td>
                            <td className="p-2 font-mono text-[#a08e7a]">{f.geometry.coordinates[1].toFixed(2)}, {f.geometry.coordinates[0].toFixed(2)}</td>
                            <td className="p-2 text-right">{num(f.properties.frp_mw, 1)}</td>
                          </tr>
                        ))}
                        {features.length === 0 && (
                          <tr><td colSpan={5} className="p-5 text-center text-[#a08e7a]">No detections match.</td></tr>
                        )}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
              {!geoLoading && listLen > shown && (
                <button type="button" onClick={() => setShown((s) => s + 50)} className="mt-2 text-xs text-[#ffc174] underline">
                  Show more ({shown} of {listLen})
                </button>
              )}
              {view === 'raw' && geoMeta?.truncated && (
                <p className="text-[11px] text-[#a08e7a] mt-1">{num(geoMeta.total_matching)} detections match; first 500 loaded.</p>
              )}
            </div>

            <details className="bg-[#171b26] border border-[#262a35] rounded-lg p-3">
              <summary className="cursor-pointer text-xs font-bold text-[#dfe2f1]">How to read this</summary>
              <ul className="list-disc pl-5 mt-2 space-y-1 text-[11px] text-[#d8c3ad] leading-relaxed">
                <li>VIIRS (375 m) sees smaller fires than MODIS (1 km), so MODIS counts are lower. They are never added.</li>
                <li>The harmonized series equals NOAA-20 VIIRS. No MODIS conversion is applied, so there is no interval.</li>
                <li>Standard-processing history and provisional NRT data are kept separate.</li>
                <li>Missing coverage is a gap, never zero. A covered quiet day is a real zero.</li>
                <li>Cells exist only where standard-processing detections exist (India footprint).</li>
              </ul>
            </details>
          </>
        )}
      </div>
    </div>
  );
}
import { useEffect, useMemo, useState } from 'react';
import {
  getShortWindowAnomalies,
  type ShortWindowAnomalyData,
  type ShortWindowDay,
} from '../../../api/advanced';

type Sensor = 'viirs' | 'modis';

const nf = (v: number) => v.toLocaleString('en-US');
const compact = (v: number) =>
  v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : String(Math.round(v));
const shortDate = (iso: string) => {
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' });
};

function describe(d: ShortWindowDay): { label: string; color: string; text: string } {
  const z = d.robust_z;
  if (z == null) return { label: 'Not scored', color: '#a08e7a', text: 'text-[#a08e7a]' };
  const a = Math.abs(z);
  const dir = z >= 0 ? 'higher' : 'lower';
  if (a >= 3) return { label: `Unusual (${dir})`, color: '#ff938c', text: 'text-[#ff938c]' };
  if (a >= 2) return { label: `Clearly ${dir} than usual`, color: z >= 0 ? '#f59e0b' : '#7bd0ff', text: z >= 0 ? 'text-[#f59e0b]' : 'text-[#7bd0ff]' };
  if (a >= 1) return { label: `Slightly ${dir} than usual`, color: z >= 0 ? '#c98a2b' : '#4f9fc4', text: z >= 0 ? 'text-[#c98a2b]' : 'text-[#4f9fc4]' };
  return { label: 'Typical', color: '#6b7280', text: 'text-[#9CA3AF]' };
}

function median(values: number[]) {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export default function ShortWindowAnomalies() {
  const [sensor, setSensor] = useState<Sensor>('viirs');
  const [data, setData] = useState<ShortWindowAnomalyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getShortWindowAnomalies(sensor)
      .then((r) => active && setData(r.data))
      .catch((e) => {
        if (!active) return;
        setData(null);
        setError(e instanceof Error ? e.message : 'Unable to load the 30-day view.');
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [sensor]);

  const stats = useMemo(() => {
    const days = data?.days ?? [];
    if (days.length === 0) return null;
    const counts = days.map((d) => d.count);
    const high = days.reduce((a, b) => (b.count > a.count ? b : a));
    const low = days.reduce((a, b) => (b.count < a.count ? b : a));
    return {
      med: median(counts),
      max: Math.max(...counts),
      high,
      low,
      flagged: days.filter((d) => d.flagged).length,
    };
  }, [data]);

  const W = 900;
  const H = 230;
  const L = 46;
  const R = 10;
  const T = 12;
  const B = 28;
  const days = data?.days ?? [];
  const yMax = stats ? stats.max * 1.1 : 1;
  const bw = days.length ? (W - L - R) / days.length : 0;
  const y = (v: number) => T + (H - T - B) * (1 - v / yMax);

  const sensorName = sensor === 'viirs' ? 'VIIRS (NOAA-20)' : 'MODIS (Terra + Aqua)';

  return (
    <div className="p-5 rounded-lg bg-[#1c1f2a] border border-[#262a35]">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div className="max-w-2xl">
          <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
            Daily fire detections, last 30 days
          </h3>
          <p className="text-[11px] font-caption-mono text-[#a08e7a] mt-1 leading-relaxed">
            How many fire detections the {sensorName} satellite recorded each day, and whether a
            day was busier or quieter than the rest of this period. This is a short-term view,
            not a comparison with previous years.
          </p>
        </div>
        <select
          value={sensor}
          onChange={(e) => setSensor(e.target.value as Sensor)}
          className="bg-[#0a0e18] border border-[#262a35] rounded px-2 py-1.5 text-xs font-caption-mono text-[#dfe2f1]"
        >
          <option value="viirs">VIIRS (NOAA-20)</option>
          <option value="modis">MODIS (Terra + Aqua)</option>
        </select>
      </div>

      {loading && <p className="text-[#7bd0ff] text-xs font-caption-mono">Loading…</p>}
      {error && <p className="text-[#ffbcb7] text-xs">{error}</p>}

      {data?.warnings.map((w) => (
        <p key={w} className="text-[11px] font-caption-mono text-[#ffc174] mb-1">
          {w}
        </p>
      ))}

      {data && stats && (
        <>
          {/* Plain-language summary */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
              <p className="text-[10px] font-caption-mono text-[#a08e7a]">TYPICAL DAY</p>
              <p className="text-lg font-bold font-mono text-[#dfe2f1]">{nf(Math.round(stats.med))}</p>
              <p className="text-[10px] text-[#a08e7a]">detections (middle value)</p>
            </div>
            <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
              <p className="text-[10px] font-caption-mono text-[#a08e7a]">BUSIEST DAY</p>
              <p className="text-lg font-bold font-mono text-[#f59e0b]">{nf(stats.high.count)}</p>
              <p className="text-[10px] text-[#a08e7a]">{shortDate(stats.high.date)}</p>
            </div>
            <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
              <p className="text-[10px] font-caption-mono text-[#a08e7a]">QUIETEST DAY</p>
              <p className="text-lg font-bold font-mono text-[#7bd0ff]">{nf(stats.low.count)}</p>
              <p className="text-[10px] text-[#a08e7a]">{shortDate(stats.low.date)}</p>
            </div>
            <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
              <p className="text-[10px] font-caption-mono text-[#a08e7a]">UNUSUAL DAYS</p>
              <p className={`text-lg font-bold font-mono ${stats.flagged ? 'text-[#ff938c]' : 'text-[#10B981]'}`}>
                {stats.flagged}
              </p>
              <p className="text-[10px] text-[#a08e7a]">
                {stats.flagged ? 'days far from the rest' : 'no day stands out'}
              </p>
            </div>
          </div>

          <p className="text-xs text-[#d8c3ad] mb-3 leading-relaxed">
            {shortDate(data.window[0])} to {shortDate(data.window[1])}: {data.usable_days} days of
            data. Daily detections ranged from {nf(stats.low.count)} to {nf(stats.high.count)}.{' '}
            {stats.flagged === 0
              ? 'No single day was far enough from the others to be called unusual.'
              : `${stats.flagged} day(s) were far enough from the others to be flagged as unusual.`}
          </p>

          {/* Chart */}
          <div className="rounded bg-[#0a0e18] border border-[#262a35] p-2">
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
              aria-label="Daily detections with typical-day line">
              {[0, 0.5, 1].map((f) => {
                const v = (yMax / 1.1) * f;
                return (
                  <g key={f}>
                    <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#262a35" strokeWidth="1" />
                    <text x={L - 6} y={y(v) + 3} textAnchor="end" fontSize="10" fill="#a08e7a">
                      {compact(v)}
                    </text>
                  </g>
                );
              })}

              {days.map((d, i) => {
                const info = describe(d);
                const x = L + i * bw + bw * 0.15;
                const h = H - B - y(d.count);
                return (
                  <g key={d.date}>
                    <rect x={x} y={y(d.count)} width={bw * 0.7} height={Math.max(h, 0)}
                      fill={info.color} rx="2">
                      <title>{`${shortDate(d.date)}: ${nf(d.count)} detections - ${info.label}`}</title>
                    </rect>
                    {i % 5 === 0 && (
                      <text x={x + bw * 0.35} y={H - 10} textAnchor="middle" fontSize="10" fill="#a08e7a">
                        {shortDate(d.date)}
                      </text>
                    )}
                  </g>
                );
              })}

              <line x1={L} x2={W - R} y1={y(stats.med)} y2={y(stats.med)}
                stroke="#dfe2f1" strokeDasharray="5 4" strokeWidth="1.2" />
              <text x={W - R} y={y(stats.med) - 4} textAnchor="end" fontSize="10" fill="#dfe2f1">
                typical day
              </text>
            </svg>

            <div className="flex flex-wrap gap-x-4 gap-y-1 px-2 pb-1 text-[10px] font-caption-mono text-[#a08e7a]">
              <span><i className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: '#6b7280' }} />Typical</span>
              <span><i className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: '#c98a2b' }} />Somewhat higher</span>
              <span><i className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: '#4f9fc4' }} />Somewhat lower</span>
              <span><i className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: '#ff938c' }} />Unusual</span>
              <span>Hover a bar for details</span>
            </div>
          </div>

          <p className="mt-3 text-[11px] font-caption-mono text-[#a08e7a] leading-relaxed">
            How to read this: each day is compared with the other days in this window only. Slow
            changes over the month (for example a gradual rise) are not removed, and a quiet day
            can also mean fewer satellite passes or more cloud, not fewer fires. Detections are
            heat signals, not confirmed wildfires.
          </p>

          {/* Raw numbers, collapsed */}
          <details className="mt-3">
            <summary className="cursor-pointer text-xs font-caption-mono text-[#7bd0ff]">
              Show daily numbers
            </summary>
            <div className="mt-2 max-h-72 overflow-y-auto">
              <table className="w-full text-left font-caption-mono text-xs">
                <thead>
                  <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                    <th className="py-2 px-3">Date</th>
                    <th className="py-2 px-3 text-right">Detections</th>
                    <th className="py-2 px-3">Compared with the rest</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#262a35]">
                  {days.map((d) => {
                    const info = describe(d);
                    return (
                      <tr key={d.date} className="bg-[#171b26] text-[#dfe2f1]">
                        <td className="py-2 px-3">{shortDate(d.date)}</td>
                        <td className="py-2 px-3 text-right">{nf(d.count)}</td>
                        <td className={`py-2 px-3 ${info.text}`}>{info.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
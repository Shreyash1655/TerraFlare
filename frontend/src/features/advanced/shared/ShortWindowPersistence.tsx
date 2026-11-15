import { useEffect, useState } from 'react';
import {
  getShortWindowPersistence,
  type ShortWindowPersistenceData,
} from '../../../api/advanced';

type Sensor = 'viirs' | 'modis';

export default function ShortWindowPersistence() {
  const [sensor, setSensor] = useState<Sensor>('viirs');
  const [data, setData] = useState<ShortWindowPersistenceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getShortWindowPersistence(sensor, 100)
      .then((r) => active && setData(r.data))
      .catch((e) => {
        if (!active) return;
        setData(null);
        setError(e instanceof Error ? e.message : 'Unable to load 30-day persistence.');
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [sensor]);

  return (
    <div className="p-5 rounded-lg bg-[#1c1f2a] border border-[#262a35]">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <div>
          <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
            30-day persistence (not multi-year memory)
          </h3>
          <p className="text-[11px] font-caption-mono text-[#a08e7a] mt-1">
            Days with at least one detection per H3 cell. Cells active every day may be
            persistent heat sources and are not necessarily wildfires.
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

      {data && (
        <>
          <p className="text-[11px] font-caption-mono text-[#a08e7a] mb-2">
            {data.covered_days} covered days • {data.n_cells.toLocaleString('en-US')} cells •{' '}
            {data.cells_full.toLocaleString('en-US')} active on every covered day • showing top{' '}
            {data.cells.length}
          </p>

          {data.warnings.map((w) => (
            <p key={w} className="text-[11px] font-caption-mono text-[#ffc174] mb-1">
              {w}
            </p>
          ))}

          {data.cells.length > 0 && (
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full text-left font-caption-mono text-xs">
                <thead>
                  <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                    <th className="py-2 px-3">H3 cell</th>
                    <th className="py-2 px-3 text-right">Days active</th>
                    <th className="py-2 px-3 text-right">Share</th>
                    <th className="py-2 px-3 text-right">Detections</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#262a35]">
                  {data.cells.map((c) => (
                    <tr key={c.h3_cell} className="bg-[#171b26] text-[#dfe2f1]">
                      <td className="py-2 px-3 font-mono">{c.h3_cell}</td>
                      <td className="py-2 px-3 text-right">
                        {c.days_active}/{c.days_covered}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {c.share == null ? '—' : `${(c.share * 100).toFixed(1)}%`}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {c.detections.toLocaleString('en-US')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
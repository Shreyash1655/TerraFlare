import { useEffect, useMemo, useState } from 'react';
import { getFireMemoryCells, getFireMemoryTimeline } from '../../../api/advanced';
import type { FireMemoryCell, FireMemoryTimelineData } from '../../../api/types/advanced';
import InsufficientHistory from '../shared/InsufficientHistory';
import ShortWindowPersistence from '../shared/ShortWindowPersistence';

type MemoryClass = 'persistent' | 'emerging' | 'declining' | 'sporadic';
type SelectedClass = 'all' | MemoryClass;

const classConfig: { id: MemoryClass; label: string; description: string; color: string; border: string }[] = [
  { id: 'persistent', label: 'PERSISTENT', description: 'Cells with consistently recurring activity.', color: '#ffc174', border: 'border-[#ffc174]' },
  { id: 'emerging', label: 'EMERGING HOTSPOTS', description: 'Cells showing increasing activity.', color: '#ff938c', border: 'border-[#ff938c]' },
  { id: 'declining', label: 'DECLINING ACTIVITY', description: 'Cells showing decreasing activity.', color: '#7bd0ff', border: 'border-[#7bd0ff]' },
  { id: 'sporadic', label: 'SPORADIC', description: 'Cells with intermittent activity.', color: '#a08e7a', border: 'border-[#a08e7a]' },
];

const errText = (e: unknown, fallback: string): string => {
  const o = e as { error?: { message?: string }; message?: string } | null;
  return o?.error?.message ?? o?.message ?? fallback;
};

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'N/A';
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatSlope(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return 'N/A';
  return `${value > 0 ? '+' : ''}${value.toFixed(4)}`;
}

function formatRecurrence(value: number): string {
  if (!Number.isFinite(value)) return 'N/A';
  // Backend recurrence is a ratio: active years / years in range.
  return `${(value * 100).toFixed(1)}%`;
}

export default function FireMemoryPage() {
  const [cells, setCells] = useState<FireMemoryCell[]>([]);
  const [selectedClass, setSelectedClass] = useState<SelectedClass>('all');
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<FireMemoryTimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [dataMode, setDataMode] = useState<'fixture' | 'real' | null>(null);
  const [isSynthetic, setIsSynthetic] = useState<boolean | null>(null);
  const [yearRange, setYearRange] = useState<number[] | null>(null);
  const [apiNotes, setApiNotes] = useState<string[]>([]);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadCells() {
      try {
        setLoading(true);
        setError(null);
        const response = await getFireMemoryCells();
        if (cancelled) return;

        const receivedCells = response.data.cells ?? [];
        const d = response.data as unknown as { year_range?: number[]; notes?: string[] };
        setCells(receivedCells);
        setYearRange(d.year_range ?? null);
        setApiNotes(d.notes ?? []);
        setDataMode(response.meta.data_mode);
        setIsSynthetic(response.meta.is_synthetic);
        setSelectedCellId((current) =>
          current && receivedCells.some((c) => c.h3_cell === current)
            ? current
            : receivedCells[0]?.h3_cell ?? null,
        );
      } catch (err) {
        if (!cancelled) {
          setCells([]);
          setError(errText(err, 'Unable to load Fire Memory data.'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadCells();
    return () => { cancelled = true; };
  }, [reloadKey]);

  const filteredCells = useMemo(
    () => (selectedClass === 'all' ? cells : cells.filter((c) => c.memory_class === selectedClass)),
    [cells, selectedClass],
  );

  useEffect(() => {
    if (filteredCells.length === 0) {
      setSelectedCellId(null);
      return;
    }
    if (!filteredCells.some((c) => c.h3_cell === selectedCellId)) {
      setSelectedCellId(filteredCells[0].h3_cell);
    }
  }, [filteredCells, selectedCellId]);

  const inspectedCell = useMemo(
    () => cells.find((c) => c.h3_cell === selectedCellId) ?? null,
    [cells, selectedCellId],
  );

  useEffect(() => {
    if (!selectedCellId) {
      setTimeline(null);
      setTimelineError(null);
      return;
    }
    const cellId = selectedCellId;
    let cancelled = false;

    async function loadTimeline() {
      try {
        setTimelineLoading(true);
        setTimelineError(null);
        setTimeline(null);
        const response = await getFireMemoryTimeline(cellId);
        if (!cancelled) setTimeline(response.data);
      } catch (err) {
        if (!cancelled) setTimelineError(errText(err, 'Unable to load the selected cell timeline.'));
      } finally {
        if (!cancelled) setTimelineLoading(false);
      }
    }

    loadTimeline();
    return () => { cancelled = true; };
  }, [selectedCellId, reloadKey]);

  const classCounts = useMemo(
    () => ({
      persistent: cells.filter((c) => c.memory_class === 'persistent').length,
      emerging: cells.filter((c) => c.memory_class === 'emerging').length,
      declining: cells.filter((c) => c.memory_class === 'declining').length,
      sporadic: cells.filter((c) => c.memory_class === 'sporadic').length,
    }),
    [cells],
  );

  const maxTimelineValue = Math.max(1, ...(timeline?.annual.map((i) => i.harmonized_value) ?? [1]));

  return (
    <div className="flex flex-col w-full pb-16">
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER B INTEL • SUBSYSTEM 05
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#ffc174]">H3 SPATIAL RECURRENCE</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Spatial Fire Memory &amp; Historical Reoccurrence Map
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Identifies H3 hexagonal cells with recurring satellite hotspot activity across multiple
              years. Cells are classified as persistent, emerging, declining, or sporadic using
              recurrence and annual activity trends.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#7bd0ff]">
              H3 Spatial Grid
            </span>
            {dataMode && (
              <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#ffc174]">
                {isSynthetic ? 'SYNTHETIC FIXTURE' : 'REAL DATA'} • {dataMode.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-start gap-2">
          <span className="material-symbols-outlined text-[#f59e0b] text-base">info</span>
          <span>
            <strong className="text-[#dfe2f1]">SCIENTIFIC CONSTRAINTS:</strong>{' '}
            Recurrence indicates that satellite detections occurred in multiple calendar years within
            a spatial cell. It does not mean the same physical fire burned continuously or that a
            unique fire returned to the same location.
          </span>
        </div>
      </section>

      <div className="w-full px-6 py-6 space-y-6">
        {loading && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-10 text-center">
            <div className="text-[#7bd0ff] font-caption-mono text-sm animate-pulse">LOADING FIRE MEMORY DATA...</div>
          </div>
        )}

        {!loading && error && (
          <div className="p-4 rounded bg-[#93000a]/10 border border-[#ffb4ab]/30 space-y-2">
            <h3 className="text-[#ffb4ab] font-bold text-sm">Fire Memory request failed</h3>
            <p className="text-xs text-[#d8c3ad]">{error}</p>
            <p className="text-xs text-[#a08e7a]">
              This is a request error, not a statement about how much history exists.
            </p>
            <button
              type="button"
              onClick={() => setReloadKey((k) => k + 1)}
              className="text-[#7bd0ff] underline text-xs"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && cells.length === 0 && (
          <>
            <InsufficientHistory module="fire-memory" detail={apiNotes.join(' ') || null} />
            <ShortWindowPersistence />
          </>
        )}

        {!loading && !error && cells.length > 0 && (
          <>
            {(yearRange || apiNotes.length > 0) && (
              <div className="p-3 rounded bg-[#171b26] border border-[#262a35] text-xs text-[#d8c3ad] space-y-1">
                {yearRange && (
                  <p>
                    Complete years analysed: <strong>{yearRange[0]}–{yearRange[1]}</strong>
                  </p>
                )}
                {apiNotes.map((n) => (<p key={n} className="text-[#a08e7a]">{n}</p>))}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {classConfig.map((config) => (
                <button
                  key={config.id}
                  onClick={() => setSelectedClass(config.id)}
                  className={`p-4 rounded border text-left transition-all ${
                    selectedClass === config.id ? `bg-[#262a35] ${config.border}` : 'bg-[#1c1f2a] border-[#262a35]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-caption-mono text-[10px] uppercase font-bold" style={{ color: config.color }}>
                      {config.label}
                    </span>
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: config.color }} />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#dfe2f1]">
                    {formatNumber(classCounts[config.id])} cells
                  </div>
                  <p className="text-[11px] text-[#a08e7a] mt-1">{config.description}</p>
                </button>
              ))}
            </div>

            <button
              onClick={() => setSelectedClass('all')}
              className={`w-full p-4 rounded border text-left transition-all ${
                selectedClass === 'all' ? 'bg-[#262a35] border-[#dfe2f1]' : 'bg-[#1c1f2a] border-[#262a35]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase font-bold">ALL OBSERVED CELLS</span>
                  <div className="text-2xl font-bold font-mono text-[#dfe2f1] mt-1">{formatNumber(cells.length)} cells</div>
                  <p className="text-[11px] text-[#a08e7a] mt-1">Cells returned by the Fire Memory API (top-ranked subset if the response is truncated).</p>
                </div>
                <span className="material-symbols-outlined text-[#7bd0ff] text-2xl">grid_view</span>
              </div>
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-7 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Recurrence Ranked Cells</h3>
                  <span className="font-caption-mono text-xs text-[#7bd0ff]">{filteredCells.length} RESULTS</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-caption-mono text-xs">
                    <thead>
                      <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                        <th className="py-2.5 px-3">H3 Index</th>
                        <th className="py-2.5 px-3 text-right">Recurrence</th>
                        <th className="py-2.5 px-3 text-right">Active Years</th>
                        <th className="py-2.5 px-3 text-right">Trend Slope</th>
                        <th className="py-2.5 px-3 text-center">Class</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#262a35]">
                      {filteredCells.map((cell) => (
                        <tr
                          key={cell.h3_cell}
                          onClick={() => setSelectedCellId(cell.h3_cell)}
                          className={`cursor-pointer transition-colors ${
                            selectedCellId === cell.h3_cell
                              ? 'bg-[#262a35] text-[#ffc174]'
                              : 'bg-[#171b26] hover:bg-[#262a35]/60 text-[#dfe2f1]'
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold whitespace-nowrap">{cell.h3_cell}</td>
                          <td className="py-3 px-3 text-right font-mono font-bold">{formatRecurrence(cell.recurrence)}</td>
                          <td className="py-3 px-3 text-right">{cell.years_active}/{cell.years_in_range}</td>
                          <td className="py-3 px-3 text-right font-mono text-[#7bd0ff]">{formatSlope(cell.trend_slope)}</td>
                          <td className="py-3 px-3 text-center">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#0a0e18] text-[#ffc174]">
                              {cell.memory_class}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filteredCells.length === 0 && (
                    <div className="py-10 text-center text-[#a08e7a] font-caption-mono text-xs">
                      NO CELLS AVAILABLE FOR THIS CLASSIFICATION
                    </div>
                  )}
                </div>
              </div>

              <div className="lg:col-span-5 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-3">
                  <span className="font-caption-mono text-xs text-[#7bd0ff] font-bold">CELL LONGITUDINAL TIMELINE</span>
                  <span className="font-mono text-xs text-[#a08e7a]">
                    {inspectedCell ? inspectedCell.h3_cell : 'NO CELL SELECTED'}
                  </span>
                </div>

                {!inspectedCell && (
                  <div className="py-10 text-center text-[#a08e7a] text-xs font-caption-mono">
                    SELECT A CELL TO VIEW ITS TIMELINE
                  </div>
                )}

                {inspectedCell && (
                  <>
                    <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1]">H3 Spatial Cell</h4>
                    <p className="font-caption-mono text-xs text-[#a08e7a] mt-1">
                      Active in {inspectedCell.years_active} of {inspectedCell.years_in_range} years in the analysis period.
                    </p>

                    <div className="grid grid-cols-2 gap-3 mt-4">
                      <div className="bg-[#171b26] border border-[#262a35] rounded p-3">
                        <p className="text-[10px] font-caption-mono text-[#a08e7a]">RECURRENCE</p>
                        <p className="text-xl font-bold font-mono text-[#ffc174] mt-1">
                          {formatRecurrence(inspectedCell.recurrence)}
                        </p>
                      </div>
                      <div className="bg-[#171b26] border border-[#262a35] rounded p-3">
                        <p className="text-[10px] font-caption-mono text-[#a08e7a]">TREND SLOPE</p>
                        <p className="text-xl font-bold font-mono text-[#7bd0ff] mt-1">
                          {formatSlope(inspectedCell.trend_slope)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-6">
                      <div className="flex justify-between items-center mb-3">
                        <span className="font-caption-mono text-xs text-[#a08e7a]">ANNUAL HARMONIZED ACTIVITY</span>
                        {timeline && (
                          <span className="font-caption-mono text-[10px] text-[#7bd0ff]">
                            {timeline.annual.length} YEARS
                          </span>
                        )}
                      </div>

                      {timelineLoading && (
                        <div className="py-8 text-center text-[#7bd0ff] font-caption-mono text-xs animate-pulse">
                          LOADING CELL TIMELINE...
                        </div>
                      )}

                      {!timelineLoading && timelineError && (
                        <div className="py-5 text-center text-[#ff938c] font-caption-mono text-xs">{timelineError}</div>
                      )}

                      {!timelineLoading && !timelineError && timeline && timeline.annual.length > 0 && (
                        <div className="space-y-3 font-caption-mono text-xs">
                          {timeline.annual.map((item) => {
                            const barWidth = Math.max(0, Math.min(100, (item.harmonized_value / maxTimelineValue) * 100));
                            return (
                              <div key={item.year} className="space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="w-12 text-[#a08e7a]">{item.year}</span>
                                  <span className="font-mono text-[#dfe2f1] font-bold">{formatNumber(item.harmonized_value)}</span>
                                </div>
                                <div className="w-full h-3.5 bg-[#0a0e18] rounded overflow-hidden">
                                  <div className="h-full bg-[#f59e0b] rounded transition-all" style={{ width: `${barWidth}%` }} />
                                </div>
                                <div className="flex justify-between text-[10px] text-[#a08e7a]">
                                  <span>Lower: {formatNumber(item.lower)}</span>
                                  <span>Upper: {formatNumber(item.upper)}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {!timelineLoading && !timelineError && timeline && timeline.annual.length === 0 && (
                        <div className="py-8 text-center text-[#a08e7a] font-caption-mono text-xs">
                          NO ANNUAL TIMELINE DATA AVAILABLE
                        </div>
                      )}
                    </div>

                    <div className="mt-6 pt-3 border-t border-[#262a35] flex flex-wrap justify-between gap-2 font-caption-mono text-xs text-[#a08e7a]">
                      <span>
                        Classification:{' '}
                        <strong className="text-[#ffc174] uppercase">{inspectedCell.memory_class}</strong>
                      </span>
                      <span>
                        Active years: <strong className="text-[#7bd0ff]">{inspectedCell.years_active}</strong>
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="bg-[#171b26] border border-[#262a35] rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-[#7bd0ff]">science</span>
                <div>
                  <h3 className="font-caption-mono text-xs font-bold text-[#dfe2f1]">METHODOLOGY &amp; INTERPRETATION</h3>
                  <p className="text-xs text-[#a08e7a] mt-2 leading-relaxed">
                    Recurrence is the proportion of complete years with detected activity relative to the
                    years in the analysis range. Incomplete years are excluded, not treated as zero. The
                    trend slope summarizes the direction of annual activity over time. These
                    classifications describe satellite-observed patterns and should not be interpreted as
                    confirmed fire events, burned area, or future fire predictions.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
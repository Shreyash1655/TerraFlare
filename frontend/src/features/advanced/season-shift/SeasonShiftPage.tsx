import { useEffect, useState } from 'react';
import { getSeasonShift } from '../../../api/advanced';
import type { SeasonShiftData } from '../../../api/types/advanced';
import InsufficientHistory from '../shared/InsufficientHistory';
import ShortWindowAnomalies from '../shared/ShortWindowAnomalies';
import FireMemoryPage from '../fire-memory/FireMemoryPage';
import AnomalyPage from '../anomaly/AnomalyPage';
import EventsPage from '../events/EventsPage';
import ExposurePage from '../exposure/ExposurePage';

type Tab = 'shift' | 'memory' | 'anomaly' | 'cluster';
type YearExtra = { status?: string; is_partial?: boolean; missing_days?: number };

const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

const errText = (e: unknown): string => {
  const o = e as { error?: { message?: string }; message?: string } | null;
  return o?.error?.message ?? o?.message ?? 'Unable to load season shift data.';
};

const doyOf = (iso?: string | null): number | null => {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return Math.round((d.getTime() - Date.UTC(d.getUTCFullYear(), 0, 0)) / 86400000);
};

const dayLabel = (iso?: string | null): string => {
  if (!iso) return 'not available';
  const d = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(d.getTime())
    ? 'not available'
    : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
};

const doyLabel = (doy: number): string =>
  new Date(Date.UTC(2001, 0, doy)).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', timeZone: 'UTC',
  });

const median = (v: number[]): number | null => {
  if (v.length === 0) return null;
  const s = [...v].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

function describeShift(
  what: 'starts' | 'ends',
  est: number | null | undefined,
  ci: (number | null | undefined)[] | undefined,
): string {
  if (est == null) {
    return `Not enough seasons to estimate when the season ${what}.`;
  }
  const days = Math.abs(est);
  const dir = est < 0 ? 'earlier' : 'later';
  const lo = ci?.[0];
  const hi = ci?.[1];
  const range =
    lo != null && hi != null
      ? ` The uncertainty range is ${lo.toFixed(0)} to ${hi.toFixed(0)} days${
          lo <= 0 && hi >= 0 ? ', which includes zero (no change)' : ''
        }.`
      : '';
  return `The season ${what} about ${days.toFixed(0)} day${days === 1 ? '' : 's'} ${dir} in recent years.${range}`;
}

export default function SeasonShiftPage() {
  const [activeTab, setActiveTab] = useState<Tab>('shift');
  const [seasonData, setSeasonData] = useState<SeasonShiftData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab !== 'shift') return;
    let cancelled = false;

    async function loadSeasonShift() {
      setLoading(true);
      setError(null);
      try {
        const response = await getSeasonShift();
        if (!cancelled) setSeasonData(response.data);
      } catch (err) {
        if (!cancelled) setError(errText(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadSeasonShift();
    return () => { cancelled = true; };
  }, [activeTab]);

  const comparison = seasonData?.comparison;
  const onsetShift = comparison?.onset_shift_days.estimate;
  const endShift = comparison?.end_shift_days.estimate;
  const peakChange = comparison?.peak_month_change;
  const baseline = comparison?.baseline;
  const recent = comparison?.recent;

  const nYears = seasonData?.years?.length ?? 0;
  const noEstimate = onsetShift == null && endShift == null && peakChange == null;

  const insufficient =
    activeTab === 'shift' &&
    !loading &&
    (!!error || (seasonData !== null && (!comparison || nYears < 2 || noEstimate)));

  const insufficientDetail =
    error ??
    (seasonData
      ? `Season shift needs at least two complete seasons and a computed baseline. This response has ${nYears} year(s) and no usable estimate, so no shift is reported.`
      : null);

  const years = seasonData?.years ?? [];
  const extra = (y: unknown) => y as YearExtra;
  const isPartial = (y: unknown) => extra(y).status === 'partial' || extra(y).is_partial === true;
  const usableYears = years.filter((y) => extra(y).status === 'ok' || extra(y).status === undefined);
  const medOnset = median(usableYears.map((y) => doyOf(y.onset)).filter((v): v is number => v != null));
  const medPeak = median(usableYears.map((y) => doyOf(y.peak)).filter((v): v is number => v != null));
  const medEnd = median(usableYears.map((y) => doyOf(y.end)).filter((v): v is number => v != null));
  const partialYears = years.filter((y) => isPartial(y));

  const evidenceLabel: string | undefined = comparison?.evidence;
  const detected = evidenceLabel === 'interval_excludes_zero';
  const notes = ((seasonData as unknown as { notes?: string[] } | null)?.notes ?? []) as string[];

  return (
    <div className="flex flex-col w-full pb-16">

      {/* SCIENTIFIC DISCLAIMER */}
      <div className="w-full px-6 py-2 bg-[#171b26] border-b border-[#262a35]">
        <div className="flex items-start gap-2.5">
          <span className="material-symbols-outlined text-[#ffc174] text-base mt-0.5 shrink-0">
            verified_user
          </span>
          <p className="font-caption-mono text-xs text-[#d8c3ad] leading-relaxed">
            <strong className="text-[#ffc174] font-medium">SCIENTIFIC DISCLAIMER:</strong>{' '}
            All intelligence models are descriptive statistical summaries of the harmonized
            satellite record. No causal climate attribution or wildfire perimeter claims are made.
            Radiometric FRP signals denote thermal sensor radiative power, subject to orbital
            sampling cadences and cloud occlusion masks.
          </p>
        </div>
      </div>

      {/* NAVIGATION */}
      <div className="w-full px-6 bg-[#1c1f2a] border-b border-[#262a35]">
        <div className="flex items-center gap-3 overflow-x-auto py-2">
          {([
            ['shift', 'trending_up', 'Phenological Fire Season Shift', 'TIER A', 'text-[#ffc174]', 'bg-[#f59e0b] text-[#0B0F19]'],
            ['memory', 'memory', 'Spatial Fire Memory Map', 'TIER B', 'text-[#7bd0ff]', 'bg-[#313540] text-[#7bd0ff]'],
            ['anomaly', 'crisis_alert', 'Explainable Anomaly Engine', 'TIER A', 'text-[#ffc174]', 'bg-[#313540] text-[#ffc174]'],
            ['cluster', 'radar', 'Cluster Tracking & Exposure', 'TIER C', 'text-[#dfe2f1]', 'bg-[#313540] text-[#a08e7a]'],
          ] as const).map(([tab, icon, label, tier, activeText, badge]) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                activeTab === tab
                  ? `bg-[#262a35] ${activeText} shadow-sm`
                  : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
              }`}
            >
              <span className="material-symbols-outlined text-base">{icon}</span>
              <span>{label}</span>
              <span className={`px-1.5 py-0.5 rounded font-caption-mono text-[9px] uppercase font-bold ml-1 ${badge}`}>
                {tier}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="w-full px-6 py-6 flex flex-col gap-6">

        {activeTab === 'shift' && loading && (
          <div className="p-4 bg-[#1c1f2a] border border-[#262a35] rounded text-[#7bd0ff] font-caption-mono text-sm">
            <span className="material-symbols-outlined align-middle mr-2 animate-spin">progress_activity</span>
            Loading Season Shift data from TerraFlare API...
          </div>
        )}

        {insufficient && (
          <>
            <InsufficientHistory module="season-shift" detail={insufficientDetail} />
            <ShortWindowAnomalies />
          </>
        )}

        {activeTab === 'shift' && !loading && !error && seasonData && !insufficient && (
          <div className="flex flex-col gap-6">

            {/* WHAT THIS PAGE ANSWERS */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg">
              <h2 className="text-lg font-bold text-[#dfe2f1]">Is the fire season changing?</h2>
              <p className="text-sm text-[#d8c3ad] mt-1 leading-relaxed">
                Every year has a fire season: a stretch of months when satellites detect the most
                heat anomalies. This page checks whether the season now starts or ends earlier or
                later than it did in earlier years ({baseline?.[0]}–{baseline?.[1]} compared with{' '}
                {recent?.[0]}–{recent?.[1]}).
              </p>
            </div>

            {/* VERDICT */}
            <div
              className={`p-5 rounded-lg border ${
                detected ? 'border-[#f59e0b]/60 bg-[#f59e0b]/10' : 'border-[#7bd0ff]/40 bg-[#7bd0ff]/10'
              }`}
            >
              <p className="text-[10px] font-caption-mono uppercase tracking-wider text-[#a08e7a]">
                What the data says
              </p>
              <p className={`text-xl font-bold mt-1 ${detected ? 'text-[#ffc174]' : 'text-[#7bd0ff]'}`}>
                {detected
                  ? 'A shift in the fire season was detected.'
                  : 'No reliable change in the fire season can be shown.'}
              </p>
              <p className="text-sm text-[#dfe2f1] mt-2 leading-relaxed">
                {detected
                  ? 'Both the start and the end moved by more than normal year-to-year variation.'
                  : 'Recent seasons look similar to earlier ones. Any difference below is small compared with how much the season normally varies from one year to the next, so it cannot be called a real change.'}
              </p>
              <ul className="mt-3 space-y-1 text-sm text-[#d8c3ad] list-disc pl-5">
                <li>{describeShift('starts', onsetShift, comparison?.onset_shift_days.ci)}</li>
                <li>{describeShift('ends', endShift, comparison?.end_shift_days.ci)}</li>
              </ul>
              <p className="text-xs text-[#a08e7a] mt-3">
                Confidence: {comparison?.evidence ? comparison.evidence.replaceAll('_', ' ') : 'not available'}.
                Only {usableYears.length} complete season{usableYears.length === 1 ? '' : 's'} of satellite data
                are available, which is short for judging a trend.
              </p>
            </div>

            {/* TYPICAL SEASON */}
            {medOnset != null && medPeak != null && medEnd != null && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded">
                  <p className="text-[10px] font-caption-mono uppercase text-[#7bd0ff]">Season usually starts</p>
                  <p className="text-2xl font-bold text-[#dfe2f1] mt-1">{doyLabel(medOnset)}</p>
                  <p className="text-xs text-[#a08e7a] mt-1">Typical (median) date across complete years</p>
                </div>
                <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded">
                  <p className="text-[10px] font-caption-mono uppercase text-[#ffc174]">Busiest around</p>
                  <p className="text-2xl font-bold text-[#ffc174] mt-1">{doyLabel(medPeak)}</p>
                  <p className="text-xs text-[#a08e7a] mt-1">Day with the most detections, typical year</p>
                </div>
                <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded">
                  <p className="text-[10px] font-caption-mono uppercase text-[#7bd0ff]">Season usually ends</p>
                  <p className="text-2xl font-bold text-[#dfe2f1] mt-1">{doyLabel(medEnd)}</p>
                  <p className="text-xs text-[#a08e7a] mt-1">Typical (median) date across complete years</p>
                </div>
              </div>
            )}

            {/* YEAR TIMELINES */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg">
              <h3 className="text-base font-bold text-[#dfe2f1]">Each year at a glance</h3>
              <p className="text-xs text-[#d8c3ad] mt-1 leading-relaxed">
                The bar spans from when the season started to when it ended. The bright marker is the
                busiest day. Start = the day 10% of the year&apos;s activity was reached; end = the day
                90% was reached. Incomplete years get no bar, because their end date is not a real season end.
              </p>

              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-[3.5rem_1fr_6rem] gap-3 items-end">
                  <span />
                  <div className="grid grid-cols-12 text-[10px] text-[#a08e7a] text-center">
                    {MONTHS.map((m, i) => (<span key={i}>{m}</span>))}
                  </div>
                  <span className="text-[10px] text-[#a08e7a] text-right">Length</span>
                </div>

                {years.map((year) => {
                  const partial = isPartial(year);
                  const o = doyOf(year.onset);
                  const p = doyOf(year.peak);
                  const e = doyOf(year.end);
                  return (
                    <div key={year.year} className="grid grid-cols-[3.5rem_1fr_6rem] gap-3 items-center">
                      <span className="font-mono font-bold text-sm text-[#dfe2f1]">{year.year}</span>
                      <div
                        className={`relative h-6 rounded bg-[#0a0e18] ${
                          partial ? 'border border-dashed border-[#a08e7a]' : 'border border-[#262a35]'
                        }`}
                        title={
                          partial
                            ? `${year.year}: incomplete year, season dates not final`
                            : `${year.year}: starts ${dayLabel(year.onset)}, busiest ${dayLabel(year.peak)}, ends ${dayLabel(year.end)}`
                        }
                      >
                        {!partial && o != null && e != null && (
                          <div
                            className="absolute top-0 h-full rounded bg-[#7bd0ff]/40"
                            style={{ left: `${(o / 366) * 100}%`, width: `${((e - o) / 366) * 100}%` }}
                          />
                        )}
                        {!partial && p != null && (
                          <div
                            className="absolute top-0 h-full w-1 bg-[#f59e0b]"
                            style={{ left: `${(p / 366) * 100}%` }}
                          />
                        )}
                        {partial && (
                          <span className="absolute inset-0 flex items-center justify-center text-[10px] text-[#a08e7a]">
                            not final
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-[#d8c3ad] text-right">
                        {partial ? 'incomplete' : `${year.length_days} days`}
                      </span>
                    </div>
                  );
                })}
              </div>

              {partialYears.length > 0 && (
                <p className="text-xs text-[#ffc174] mt-4 leading-relaxed">
                  {partialYears.map((y) => y.year).join(', ')}{' '}
                  {partialYears.length === 1 ? 'is' : 'are'} incomplete: the satellite record does not
                  cover the whole year (it ends before 31 December, starts after 1 January, or too many
                  days are missing), so {partialYears.length === 1 ? 'it is' : 'they are'} left out of the
                  comparison. Missing days are never counted as &quot;no fire&quot;.
                </p>
              )}
            </div>

            {/* TABLE */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg">
              <h3 className="text-base font-bold text-[#dfe2f1]">Exact dates</h3>
              <div className="overflow-x-auto mt-3">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[#262a35] text-[#7bd0ff] font-caption-mono">
                      <th className="py-3 px-3">YEAR</th>
                      <th className="py-3 px-3">SEASON STARTS</th>
                      <th className="py-3 px-3">BUSIEST DAY</th>
                      <th className="py-3 px-3">SEASON ENDS</th>
                      <th className="py-3 px-3">LENGTH</th>
                      <th className="py-3 px-3">DATA</th>
                      <th className="py-3 px-3">MISSING DAYS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {years.map((year) => {
                      const ex = extra(year);
                      const partial = isPartial(year);
                      return (
                        <tr key={year.year} className="border-b border-[#262a35] text-[#dfe2f1]">
                          <td className="py-3 px-3 font-bold font-mono">{year.year}</td>
                          <td className="py-3 px-3">
                            {year.onset ? `${year.onset}${partial ? ' (provisional)' : ''}` : 'not available'}
                          </td>
                          <td className="py-3 px-3 text-[#ffc174]">
                            {year.peak ? `${year.peak}${partial ? ' (provisional)' : ''}` : 'not available'}
                          </td>
                          <td className="py-3 px-3">
                            {partial ? 'not final (year incomplete)' : year.end ?? 'not available'}
                          </td>
                          <td className="py-3 px-3 font-mono">
                            {partial ? 'incomplete' : `${year.length_days} days`}
                          </td>
                          <td className="py-3 px-3">{year.sensor_mix.join(', ') || 'not available'}</td>
                          <td className="py-3 px-3">{ex.missing_days ?? 'not available'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* GLOSSARY */}
            <details className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg">
              <summary className="cursor-pointer text-base font-bold text-[#dfe2f1]">
                What do these terms mean?
              </summary>
              <dl className="mt-3 space-y-3 text-sm text-[#d8c3ad] leading-relaxed">
                <div>
                  <dt className="font-semibold text-[#dfe2f1]">Fire season</dt>
                  <dd>The months when satellite heat detections are concentrated. Here it runs from the day 10% of a year&apos;s activity has occurred to the day 90% has.</dd>
                </div>
                <div>
                  <dt className="font-semibold text-[#dfe2f1]">Shift (days)</dt>
                  <dd>How much the typical start or end date moved between the earlier and recent periods. Negative means earlier, positive means later.</dd>
                </div>
                <div>
                  <dt className="font-semibold text-[#dfe2f1]">Uncertainty range (95% interval)</dt>
                  <dd>The range of shifts that fit the data. If it includes zero, &quot;no change&quot; is just as plausible as the measured shift.</dd>
                </div>
                <div>
                  <dt className="font-semibold text-[#dfe2f1]">Insufficient evidence</dt>
                  <dd>The data cannot separate a real change from ordinary year-to-year variation. It does not mean nothing changed.</dd>
                </div>
                <div>
                  <dt className="font-semibold text-[#dfe2f1]">Peak month change</dt>
                  <dd>A rough month-to-month difference in the busiest period. It carries no uncertainty range, so it is not shown as a finding.</dd>
                </div>
              </dl>
            </details>

            {/* CAVEATS */}
            <div className="bg-[#171b26] border border-[#262a35] p-5 rounded-lg">
              <h3 className="text-sm font-bold text-[#dfe2f1]">Things to keep in mind</h3>
              <ul className="mt-2 space-y-1.5 text-xs text-[#d8c3ad] list-disc pl-5 leading-relaxed">
                <li>The data is satellite heat detections (NOAA-20 VIIRS). These are thermal anomalies, not a count of separate fires.</li>
                <li>Only {usableYears.length} complete years are available. That is short for judging a long-term trend.</li>
                <li>The two comparison periods overlap (they share 2023–2025), which limits what the comparison can prove.</li>
                {partialYears.length > 0 && (
                  <li>
                    {partialYears.map((y) => y.year).join(', ')}{' '}
                    {partialYears.length === 1 ? 'is' : 'are'} not a complete year of data, so{' '}
                    {partialYears.length === 1 ? 'it is' : 'they are'} excluded rather than treated as a quiet
                    season. Dates shown for {partialYears.length === 1 ? 'it' : 'them'} are provisional.
                  </li>
                )}
                <li>This page describes timing only. It does not say why the season looks the way it does.</li>
                {notes.map((n) => (<li key={n}>{n}</li>))}
              </ul>
            </div>

          </div>
        )}

        {activeTab === 'memory' && <FireMemoryPage />}
        {activeTab === 'anomaly' && <AnomalyPage />}
        {activeTab === 'cluster' && (
          <>
            <EventsPage />
            <ExposurePage />
          </>
        )}

      </div>
    </div>
  );
}
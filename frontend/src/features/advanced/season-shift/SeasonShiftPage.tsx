
import { useEffect, useState } from 'react';
import { getSeasonShift } from '../../../api/advanced';
import type { SeasonShiftData } from '../../../api/types/advanced';

type Tab = 'shift' | 'memory' | 'anomaly' | 'cluster';

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

        if (!cancelled) {
          setSeasonData(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load season shift data.'
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSeasonShift();

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  const comparison = seasonData?.comparison;

  const onsetShift = comparison?.onset_shift_days.estimate;
  const endShift = comparison?.end_shift_days.estimate;
  const peakChange = comparison?.peak_month_change;

  const baseline = comparison?.baseline;
  const recent = comparison?.recent;

  const formatValue = (value: number | null | undefined) =>
    value == null ? 'N/A' : value.toFixed(1);

  return (
    <div className="flex flex-col w-full pb-16">

      {/* SCIENTIFIC DISCLAIMER */}
      <div className="w-full px-6 py-2 bg-[#171b26] border-b border-[#262a35]">
        <div className="flex items-start gap-2.5">
          <span className="material-symbols-outlined text-[#ffc174] text-base mt-0.5 shrink-0">
            verified_user
          </span>

          <p className="font-caption-mono text-xs text-[#d8c3ad] leading-relaxed">
            <strong className="text-[#ffc174] font-medium">
              SCIENTIFIC DISCLAIMER:
            </strong>{' '}
            All intelligence models are descriptive statistical summaries of
            the harmonized satellite record. No causal climate attribution or
            wildfire perimeter claims are made. Radiometric FRP signals denote
            thermal sensor radiative power, subject to orbital sampling
            cadences and cloud occlusion masks.
          </p>
        </div>
      </div>

      {/* NAVIGATION */}
      <div className="w-full px-6 bg-[#1c1f2a] border-b border-[#262a35]">
        <div className="flex items-center gap-3 overflow-x-auto py-2">

          <button
            onClick={() => setActiveTab('shift')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === 'shift'
                ? 'bg-[#262a35] text-[#ffc174] shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
            }`}
          >
            <span className="material-symbols-outlined text-base">
              trending_up
            </span>
            <span>Phenological Fire Season Shift</span>
            <span className="px-1.5 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-[9px] uppercase font-bold ml-1">
              TIER A
            </span>
          </button>

          <button
            onClick={() => setActiveTab('memory')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === 'memory'
                ? 'bg-[#262a35] text-[#7bd0ff] shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
            }`}
          >
            <span className="material-symbols-outlined text-base">
              memory
            </span>
            <span>Spatial Fire Memory Map</span>
            <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#7bd0ff] font-caption-mono text-[9px] uppercase font-bold ml-1">
              TIER B
            </span>
          </button>

          <button
            onClick={() => setActiveTab('anomaly')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === 'anomaly'
                ? 'bg-[#262a35] text-[#ffc174] shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
            }`}
          >
            <span className="material-symbols-outlined text-base">
              crisis_alert
            </span>
            <span>Explainable Anomaly Engine</span>
            <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#ffc174] font-caption-mono text-[9px] uppercase font-bold ml-1">
              TIER A
            </span>
          </button>

          <button
            onClick={() => setActiveTab('cluster')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === 'cluster'
                ? 'bg-[#262a35] text-[#dfe2f1] shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
            }`}
          >
            <span className="material-symbols-outlined text-base">
              radar
            </span>
            <span>Cluster Tracking &amp; Exposure</span>
            <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#a08e7a] font-caption-mono text-[9px] uppercase font-bold ml-1">
              TIER C
            </span>
          </button>

        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="w-full px-6 py-6 flex flex-col gap-6">

        {/* LOADING */}
        {activeTab === 'shift' && loading && (
          <div className="p-4 bg-[#1c1f2a] border border-[#262a35] rounded text-[#7bd0ff] font-caption-mono text-sm">
            <span className="material-symbols-outlined align-middle mr-2 animate-spin">
              progress_activity
            </span>
            Loading Season Shift data from TerraFlare API...
          </div>
        )}

        {/* ERROR */}
        {activeTab === 'shift' && error && (
          <div className="p-4 bg-[#1c1f2a] border border-[#ff938c] rounded text-[#ff938c]">
            <div className="font-bold mb-2">
              Unable to load Season Shift data
            </div>

            <p className="text-sm">{error}</p>

            <button
              onClick={() => {
                setSeasonData(null);
                setActiveTab('memory');
                setTimeout(() => setActiveTab('shift'), 0);
              }}
              className="mt-3 px-3 py-2 bg-[#313540] rounded text-xs"
            >
              Retry
            </button>
          </div>
        )}

        {/* SEASON SHIFT */}
        {activeTab === 'shift' && !loading && !error && seasonData && (
          <div className="flex flex-col gap-6">

            {/* DATA PERIOD */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs font-caption-mono text-[#a08e7a]">
                BASELINE: {baseline?.[0]}–{baseline?.[1]}
                <span className="mx-2">|</span>
                RECENT: {recent?.[0]}–{recent?.[1]}
              </div>

              <span className="px-3 py-1.5 rounded bg-[#0a0e18] border border-[#262a35] text-[#7bd0ff] font-caption-mono text-xs">
                API RESPONSE RECEIVED
              </span>
            </div>

            {/* STATISTICS */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

              {/* ONSET */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#7bd0ff] uppercase tracking-wider">
                    PHENOLOGICAL ONSET
                  </span>
                </div>

                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">
                  Season Onset Shift
                </span>

                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174]">
                    {formatValue(onsetShift)}
                  </span>
                  <span className="font-label-mono text-xs text-[#ffc174] uppercase">
                    days
                  </span>
                </div>

                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    95% Confidence Interval:
                    <br />
                    <span className="text-[#7bd0ff] font-mono">
                      [
                      {formatValue(comparison?.onset_shift_days.ci[0])},{' '}
                      {formatValue(comparison?.onset_shift_days.ci[1])}
                      ]
                    </span>
                  </p>
                </div>
              </div>

              {/* PEAK */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#ffc174] uppercase tracking-wider">
                    PEAK CHANGE
                  </span>
                </div>

                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">
                  Season Peak Change
                </span>

                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#f59e0b]">
                    {formatValue(peakChange)}
                  </span>
                  <span className="font-label-mono text-xs text-[#f59e0b] uppercase">
                    reported change
                  </span>
                </div>

                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    Peak month change reported by the backend analysis.
                    No independent significance claim is made here.
                  </p>
                </div>
              </div>

              {/* END */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#7bd0ff] uppercase tracking-wider">
                    SEASON CESSATION
                  </span>
                </div>

                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">
                  Season End Shift
                </span>

                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff]">
                    {formatValue(endShift)}
                  </span>
                  <span className="font-label-mono text-xs text-[#7bd0ff] uppercase">
                    days
                  </span>
                </div>

                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    95% Confidence Interval:
                    <br />
                    <span className="text-[#7bd0ff] font-mono">
                      [
                      {formatValue(comparison?.end_shift_days.ci[0])},{' '}
                      {formatValue(comparison?.end_shift_days.ci[1])}
                      ]
                    </span>
                  </p>
                </div>
              </div>

              {/* EVIDENCE */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#ffb4ab] uppercase tracking-wider">
                    STATISTICAL EVIDENCE
                  </span>
                </div>

                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">
                  Evidence Assessment
                </span>

                <div className="my-2">
                  <span className="font-mono-metric-lg text-lg font-bold text-[#ffc174]">
                    {comparison?.evidence
                      ? comparison.evidence.replaceAll('_', ' ').toUpperCase()
                      : 'N/A'}
                  </span>
                </div>

                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    Evidence classification returned by the backend analysis.
                  </p>
                </div>
              </div>

            </div>

            {/* YEARLY DATA */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md">

              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="font-headline-sm text-base font-bold text-[#dfe2f1]">
                    Annual Fire Season Milestones
                  </h3>

                  <p className="font-body-sm text-xs text-[#d8c3ad] mt-1">
                    Annual onset, peak and cessation dates returned by the
                    harmonized satellite analysis.
                  </p>
                </div>

                <span className="px-3 py-1.5 rounded bg-[#0a0e18] border border-[#262a35] text-[#7bd0ff] font-caption-mono text-xs">
                  {seasonData.years.length} YEARS
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[#262a35] text-[#7bd0ff] font-caption-mono">
                      <th className="py-3 px-3">YEAR</th>
                      <th className="py-3 px-3">ONSET</th>
                      <th className="py-3 px-3">PEAK</th>
                      <th className="py-3 px-3">END</th>
                      <th className="py-3 px-3">LENGTH</th>
                      <th className="py-3 px-3">SENSORS</th>
                    </tr>
                  </thead>

                  <tbody>
                    {seasonData.years.map((year) => (
                      <tr
                        key={year.year}
                        className="border-b border-[#262a35] text-[#dfe2f1] hover:bg-[#262a35]/50"
                      >
                        <td className="py-3 px-3 font-bold font-mono">
                          {year.year}
                        </td>
                        <td className="py-3 px-3">{year.onset}</td>
                        <td className="py-3 px-3 text-[#ffc174]">
                          {year.peak}
                        </td>
                        <td className="py-3 px-3">{year.end}</td>
                        <td className="py-3 px-3 font-mono">
                          {year.length_days} days
                        </td>
                        <td className="py-3 px-3">
                          {year.sensor_mix.join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* COMPARISON PERIODS */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md">
              <h3 className="font-headline-sm text-base font-bold text-[#dfe2f1] mb-3">
                Season Comparison
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[#0a0e18] p-4 rounded border border-[#262a35]">
                  <p className="text-[#a08e7a] font-caption-mono text-xs mb-2">
                    BASELINE PERIOD
                  </p>
                  <p className="text-[#dfe2f1] text-xl font-bold font-mono">
                    {baseline?.[0]} – {baseline?.[1]}
                  </p>
                </div>

                <div className="bg-[#0a0e18] p-4 rounded border border-[#262a35]">
                  <p className="text-[#a08e7a] font-caption-mono text-xs mb-2">
                    RECENT PERIOD
                  </p>
                  <p className="text-[#dfe2f1] text-xl font-bold font-mono">
                    {recent?.[0]} – {recent?.[1]}
                  </p>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* FIRE MEMORY */}
        {activeTab === 'memory' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  Spatial Fire Memory &amp; Reoccurrence Map
                </h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  Classifying H3 cells into persistent, emerging, declining,
                  or sporadic activity
                </span>
              </div>

              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs font-bold">
                MULTI-YEAR RECURRENCE
              </span>
            </div>

            <p className="text-sm text-[#d8c3ad]">
              Fire Memory API integration is pending. Live data will appear
              here after connecting the Fire Memory endpoints.
            </p>
          </div>
        )}

        {/* ANOMALY */}
        {activeTab === 'anomaly' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  Explainable Wildfire Anomaly Engine
                </h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  Robust Z-score and MAD excess decomposition by date and cell
                </span>
              </div>
            </div>

            <p className="text-sm text-[#d8c3ad]">
              Anomaly API integration is pending. Live anomaly results will
              appear here after connecting the Anomaly endpoints.
            </p>
          </div>
        )}

        {/* EVENTS AND EXPOSURE */}
        {activeTab === 'cluster' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">
                  Activity Episode Clustering &amp; Exposure
                </h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  DBSCAN spatiotemporal clustering with asset proximity buffers
                </span>
              </div>

              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#a08e7a] font-caption-mono text-xs">
                EVENT INTELLIGENCE
              </span>
            </div>

            <p className="font-body-sm text-xs text-[#d8c3ad]">
              Clusters represent spatiotemporally grouped active fire
              detections (activity episodes), not verified burn perimeters.
              Exposure metrics denote geographical proximity within
              configured buffer zones.
            </p>

            <p className="text-sm text-[#d8c3ad]">
              Events and Exposure API integration is pending.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}

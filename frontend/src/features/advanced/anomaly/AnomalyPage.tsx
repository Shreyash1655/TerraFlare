
import { useEffect, useMemo, useState } from 'react';
import { getAnomalies, getAnomalyExplain } from '../../../api/advanced';
import type {
  AnomaliesData,
  AnomalyPeriod,
  AnomalyExplainData,
} from '../../../api/types/advanced';

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
  });
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

function formatPeriod(start: string, end: string) {
  return `${formatDate(start)} – ${formatDate(end)}`;
}

function formatShare(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }

  const percentage = value <= 1 ? value * 100 : value;

  return `${percentage.toFixed(1)}%`;
}

function getAnomalyStatus(score: number | null) {
  if (score === null || !Number.isFinite(score)) {
    return 'Score Unavailable';
  }

  const magnitude = Math.abs(score);

  if (magnitude >= 3) return 'Extreme Statistical Deviation';
  if (magnitude >= 2) return 'Strong Statistical Deviation';
  if (magnitude >= 1) return 'Elevated Deviation';

  return 'Within Expected Variation';
}

function getStatusStyle(score: number | null) {
  if (score === null || !Number.isFinite(score)) {
    return 'bg-[#262a35] text-[#a08e7a]';
  }

  const magnitude = Math.abs(score);

  if (magnitude >= 3) {
    return 'bg-[#93000a]/20 text-[#ffb4ab]';
  }

  if (magnitude >= 2) {
    return 'bg-[#754b1c]/30 text-[#ffc174]';
  }

  if (magnitude >= 1) {
    return 'bg-[#17415a]/40 text-[#7bd0ff]';
  }

  return 'bg-[#262a35] text-[#a08e7a]';
}

function getBarWidth(share: number | null | undefined) {
  if (share === null || share === undefined || !Number.isFinite(share)) {
    return 0;
  }

  const percentage = share <= 1 ? share * 100 : share;

  return Math.max(0, Math.min(100, percentage));
}

export default function AnomalyPage() {
  const [anomalies, setAnomalies] = useState<AnomalyPeriod[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);

  const [explanation, setExplanation] =
    useState<AnomalyExplainData | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  const [dataMode, setDataMode] = useState<'fixture' | 'real'>('fixture');
  const [isSynthetic, setIsSynthetic] = useState(false);

  // Fetch anomaly periods.
  useEffect(() => {
    let active = true;

    async function loadAnomalies() {
      try {
        setLoading(true);
        setError(null);

        const response = await getAnomalies();

        if (!active) return;

        const data: AnomaliesData = response.data;
        const periods = data.periods ?? [];

        setAnomalies(periods);
        setDataMode(response.meta.data_mode);
        setIsSynthetic(response.meta.is_synthetic);

        setSelectedPeriod((current) => {
          if (
            current &&
            periods.some((item) => item.period_start === current)
          ) {
            return current;
          }

          return periods[0]?.period_start ?? null;
        });
      } catch (err) {
        if (!active) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load anomaly periods.',
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    loadAnomalies();

    return () => {
      active = false;
    };
  }, []);

  // Fetch explanation for the selected anomaly.
  useEffect(() => {
    if (!selectedPeriod) {
      setExplanation(null);
      setExplanationError(null);
      setLoadingExplanation(false);
      return;
    }

    const periodStart = selectedPeriod;
    let active = true;

    async function loadExplanation() {
      try {
        setLoadingExplanation(true);
        setExplanationError(null);
        setExplanation(null);

        const response = await getAnomalyExplain({
          period_start: periodStart,
        });

        if (!active) return;

        setExplanation(response.data);
      } catch (err) {
        if (!active) return;

        setExplanationError(
          err instanceof Error
            ? err.message
            : 'Unable to load the anomaly explanation.',
        );
      } finally {
        if (active) setLoadingExplanation(false);
      }
    }

    loadExplanation();

    return () => {
      active = false;
    };
  }, [selectedPeriod]);

  const selectedAnomaly = useMemo(
    () =>
      anomalies.find((item) => item.period_start === selectedPeriod) ?? null,
    [anomalies, selectedPeriod],
  );

  const topDates = explanation?.top_dates ?? [];
  const topCells = explanation?.top_cells ?? [];
  const explanationPeriod = explanation?.period;

  const selectedRobustZ = selectedAnomaly?.robust_z ?? null;

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER A INTEL • SUBSYSTEM 06
              </span>

              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>

              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                ROBUST Z &amp; MAD DECOMPOSITION
              </span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Explainable Wildfire Anomaly Engine
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Detects periods where fire activity differs from historical
              seasonal baselines. Explore robust statistical scores,
              contributing observation dates and spatial H3 cells.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#ff938c]">
              {selectedRobustZ === null
                ? 'ROBUST Z: —'
                : `ROBUST Z: ${selectedRobustZ >= 0 ? '+' : ''}${formatNumber(selectedRobustZ)}`}
            </span>
          </div>
        </div>

        {/* Data Mode */}
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <span className="px-2 py-1 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#7bd0ff]">
            DATA MODE: {dataMode.toUpperCase()}
          </span>

          {isSynthetic && (
            <span className="px-2 py-1 rounded bg-[#30251a] border border-[#70502b] text-xs font-caption-mono text-[#ffc174]">
              SYNTHETIC DATA — NOT OBSERVED FIRE ACTIVITY
            </span>
          )}
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-start gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">
            warning
          </span>

          <span>
            <strong className="text-[#dfe2f1]">
              SCIENTIFIC CONSTRAINTS:
            </strong>{' '}
            An anomaly score is a descriptive statistical deviation from a
            historical baseline. It does not establish causal attribution or
            identify weather, climate or human factors.
          </span>
        </div>
      </section>

      {/* Main Analysis Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Loading */}
        {loading && (
          <div className="p-8 text-center rounded-lg bg-[#1c1f2a] border border-[#262a35]">
            <p className="text-[#7bd0ff] font-caption-mono text-sm">
              Analysing historical anomaly periods...
            </p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="p-5 rounded-lg bg-[#301b20] border border-[#75343d]">
            <p className="text-[#ffbcb7] font-semibold text-sm">
              Unable to load anomaly data
            </p>

            <p className="text-[#d8c3ad] text-xs mt-2">{error}</p>

            <button
              onClick={() => window.location.reload()}
              className="mt-3 px-3 py-2 rounded bg-[#ffc174] text-[#0a0e18] text-xs font-bold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && anomalies.length === 0 && (
          <div className="p-8 text-center rounded-lg bg-[#1c1f2a] border border-[#262a35]">
            <span className="material-symbols-outlined text-3xl text-[#a08e7a]">
              analytics
            </span>

            <p className="text-[#dfe2f1] font-semibold mt-2">
              No anomaly periods found
            </p>

            <p className="text-[#a08e7a] text-xs mt-1">
              The current dataset does not contain any scored anomaly periods.
            </p>
          </div>
        )}

        {!loading && !error && anomalies.length > 0 && (
          <>
            {/* Statistical Explanation */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">
                  psychology
                </span>

                <h2 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                  Deterministic Statistical Explanation
                </h2>
              </div>

              <div className="p-4 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs text-[#dfe2f1] leading-relaxed">
                <p className="text-[#ffc174] font-bold mb-2">
                  BACKEND-GENERATED EXPLANATION
                </p>

                {loadingExplanation && (
                  <p className="text-[#7bd0ff]">
                    Generating explanation for the selected period...
                  </p>
                )}

                {!loadingExplanation && explanationError && (
                  <p className="text-[#ffbcb7]">{explanationError}</p>
                )}

                {!loadingExplanation && !explanationError && explanation && (
                  <>
                    <p>
                      {explanation.explanation ||
                        'No textual explanation is available for this period.'}
                    </p>

                    <div className="grid grid-cols-2 gap-3 mt-4">
                      <div className="p-3 rounded bg-[#171b26]">
                        <span className="text-[#a08e7a] block text-[10px]">
                          ROBUST Z-SCORE
                        </span>

                        <span className="text-[#ff938c] font-bold text-base">
                          {formatNumber(explanation.score.robust_z)}
                        </span>
                      </div>

                      <div className="p-3 rounded bg-[#171b26]">
                        <span className="text-[#a08e7a] block text-[10px]">
                          PERCENTILE
                        </span>

                        <span className="text-[#7bd0ff] font-bold text-base">
                          {formatNumber(explanation.score.percentile)}%
                        </span>
                      </div>
                    </div>
                  </>
                )}

                {!loadingExplanation &&
                  !explanationError &&
                  !explanation && (
                    <p className="text-[#a08e7a]">
                      Select an anomaly period to view its explanation.
                    </p>
                  )}
              </div>
            </div>

            {/* Ranked Anomaly Periods */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
              <div className="flex items-center justify-between gap-3 mb-3">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                  Scored Historical Anomaly Periods
                </h3>

                <span className="font-caption-mono text-xs text-[#7bd0ff]">
                  {anomalies.length} PERIODS
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-caption-mono text-xs">
                  <thead>
                    <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                      <th className="py-2.5 px-3">Target Period</th>
                      <th className="py-2.5 px-3 text-right">Observed</th>
                      <th className="py-2.5 px-3 text-right">
                        Baseline Median
                      </th>
                      <th className="py-2.5 px-3 text-right">Robust Z</th>
                      <th className="py-2.5 px-3 text-right">Percentile</th>
                      <th className="py-2.5 px-3 text-center">
                        Classification
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-[#262a35]">
                    {anomalies.map((anomaly) => {
                      const isSelected =
                        selectedPeriod === anomaly.period_start;

                      const robustZ = anomaly.robust_z ?? null;

                      return (
                        <tr
                          key={anomaly.period_start}
                          onClick={() =>
                            setSelectedPeriod(anomaly.period_start)
                          }
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-[#262a35] text-[#ffc174]'
                              : 'bg-[#171b26] hover:bg-[#262a35]/60 text-[#dfe2f1]'
                          }`}
                        >
                          <td className="py-3 px-3 font-bold whitespace-nowrap">
                            {formatPeriod(
                              anomaly.period_start,
                              anomaly.period_end,
                            )}
                          </td>

                          <td className="py-3 px-3 text-right font-mono font-bold">
                            {formatNumber(anomaly.observed)}
                          </td>

                          <td className="py-3 px-3 text-right font-mono text-[#a08e7a]">
                            {formatNumber(anomaly.baseline_median)}
                          </td>

                          <td className="py-3 px-3 text-right font-mono font-bold text-[#ff938c]">
                            {robustZ === null
                              ? '—'
                              : `${robustZ >= 0 ? '+' : ''}${formatNumber(robustZ)}`}
                          </td>

                          <td className="py-3 px-3 text-right font-mono text-[#7bd0ff]">
                            {formatNumber(anomaly.percentile)}%
                          </td>

                          <td className="py-3 px-3 text-center">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${getStatusStyle(robustZ)}`}
                            >
                              {getAnomalyStatus(robustZ)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <p className="mt-3 text-[10px] font-caption-mono text-[#a08e7a]">
                Classification is derived from the absolute robust Z-score and
                is descriptive, not a verified fire-severity category.
              </p>
            </div>

            {/* Decomposition: Dates & Cells */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Dates */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">
                  Excess Attributed by Observation Date
                </h3>

                <span className="font-caption-mono text-xs text-[#a08e7a] block mb-3">
                  Dates contributing to the selected anomaly
                </span>

                {loadingExplanation && (
                  <p className="text-[#7bd0ff] text-xs font-caption-mono">
                    Loading contributing dates...
                  </p>
                )}

                {!loadingExplanation &&
                  !explanationError &&
                  topDates.length === 0 && (
                    <p className="p-4 rounded bg-[#171b26] text-[#a08e7a] text-xs">
                      No contributing date breakdown is available.
                    </p>
                  )}

                {!loadingExplanation && (
                  <div className="space-y-3 font-caption-mono text-xs">
                    {topDates.map((item) => (
                      <div
                        key={item.date}
                        className="p-2.5 rounded bg-[#171b26] border border-[#262a35]"
                      >
                        <div className="flex justify-between items-center mb-1 gap-2">
                          <span className="font-bold text-[#dfe2f1]">
                            {formatDate(item.date)}
                          </span>

                          <span className="text-[#ffc174] font-bold">
                            +{formatNumber(item.excess)} (
                            {formatShare(item.share)})
                          </span>
                        </div>

                        <div className="w-full bg-[#0a0e18] h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-[#f59e0b] h-full rounded-full"
                            style={{
                              width: `${getBarWidth(item.share)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Top H3 Cells */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">
                  Excess Attributed by H3 Hexagon Cell
                </h3>

                <span className="font-caption-mono text-xs text-[#a08e7a] block mb-3">
                  Spatial cells contributing to the selected anomaly
                </span>

                {loadingExplanation && (
                  <p className="text-[#7bd0ff] text-xs font-caption-mono">
                    Loading contributing cells...
                  </p>
                )}

                {!loadingExplanation &&
                  !explanationError &&
                  topCells.length === 0 && (
                    <p className="p-4 rounded bg-[#171b26] text-[#a08e7a] text-xs">
                      No contributing H3 cell breakdown is available.
                    </p>
                  )}

                {!loadingExplanation && (
                  <div className="space-y-3 font-caption-mono text-xs">
                    {topCells.map((cell) => (
                      <div
                        key={cell.h3_cell}
                        className="p-2.5 rounded bg-[#171b26] border border-[#262a35]"
                      >
                        <div className="flex justify-between items-center mb-1 gap-2">
                          <span className="font-bold text-[#dfe2f1] break-all">
                            {cell.h3_cell}
                          </span>

                          <span className="text-[#7bd0ff] font-bold whitespace-nowrap">
                            +{formatNumber(cell.excess)} (
                            {formatShare(cell.share)})
                          </span>
                        </div>

                        <div className="w-full bg-[#0a0e18] h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-[#7bd0ff] h-full rounded-full"
                            style={{
                              width: `${getBarWidth(cell.share)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Analysis Context */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-4">
              <h3 className="font-title-sm text-xs font-bold text-[#dfe2f1] mb-2">
                ANALYSIS CONTEXT
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-caption-mono text-xs">
                <div>
                  <span className="text-[#a08e7a] block text-[10px]">
                    SELECTED PERIOD
                  </span>

                  <span className="text-[#dfe2f1]">
                    {explanationPeriod
                      ? formatPeriod(
                          explanationPeriod.start,
                          explanationPeriod.end,
                        )
                      : selectedAnomaly
                        ? formatPeriod(
                            selectedAnomaly.period_start,
                            selectedAnomaly.period_end,
                          )
                        : '—'}
                  </span>
                </div>

                <div>
                  <span className="text-[#a08e7a] block text-[10px]">
                    BASELINE YEARS
                  </span>

                  <span className="text-[#dfe2f1]">
                    {selectedAnomaly?.n_baseline_years ?? '—'}
                  </span>
                </div>

                <div>
                  <span className="text-[#a08e7a] block text-[10px]">
                    OBSERVED EXCESS
                  </span>

                  <span className="text-[#ffc174] font-bold">
                    {selectedAnomaly
                      ? formatNumber(
                          selectedAnomaly.observed -
                            selectedAnomaly.baseline_median,
                        )
                      : '—'}
                  </span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

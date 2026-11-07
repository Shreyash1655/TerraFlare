import { useState } from 'react';

const mockAnomalies = [
  { period: '2024-W33 (Aug 12–18)', observed: 4890, baseline: 1270, robustZ: 3.84, percentile: 99.4, excess: 3620, status: 'Extreme Outlier' },
  { period: '2024-W34 (Aug 19–25)', observed: 3150, baseline: 1180, robustZ: 2.62, percentile: 96.8, excess: 1970, status: 'Severe Anomaly' },
  { period: '2024-W32 (Aug 05–11)', observed: 2420, baseline: 1100, robustZ: 2.14, percentile: 94.2, excess: 1320, status: 'Elevated Surge' },
];

export default function AnomalyPage() {
  const [selectedAnomaly, setSelectedAnomaly] = useState(mockAnomalies[0]);

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
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">ROBUST Z &amp; MAD DECOMPOSITION</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Explainable Wildfire Anomaly Engine
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Detects weeks where fire activity diverges significantly from comparable historical periods (±14 day seasonal window over 24 years). Quantifies exact excess thermal energy and attributes contributions to specific dates and spatial grid cells.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#ff938c]">
              ROBUST Z: +{selectedAnomaly.robustZ} (99.4th Percentile)
            </span>
          </div>
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">warning</span>
          <span>
            <strong className="text-[#dfe2f1]">SCIENTIFIC CONSTRAINTS:</strong> An anomaly score is a descriptive statistical deviation from historical baselines. It does not establish causal attribution or weather/climate factors.
          </span>
        </div>
      </section>

      {/* Main Analysis Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Template Explanation Card */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-[#ffc174] text-lg">psychology</span>
            <h2 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Deterministic Statistical Explanation</h2>
          </div>
          <div className="p-4 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs text-[#dfe2f1] leading-relaxed">
            <p className="text-[#ffc174] font-bold mb-1">AUTOMATED SYNTHESIS (NO LLM HALLUCINATION):</p>
            Thermal activity in the selected window ({selectedAnomaly.period}) was{' '}
            <strong className="text-[#ffc174]">{selectedAnomaly.robustZ} standard robust deviations</strong> above the
            historical climatological median (2000–2023). Total excess activity amounted to{' '}
            <strong className="text-[#7bd0ff]">+{selectedAnomaly.excess.toLocaleString()} eq</strong>. Three dates
            accounted for 92.1% of the excess, driven by intense thermal detections in Willamette Basin cells on August 16–18.
          </div>
        </div>

        {/* Anomaly Ranked Periods */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-3">Scored Historical Anomaly Periods</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-caption-mono text-xs">
              <thead>
                <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                  <th className="py-2.5 px-3">Target Period</th>
                  <th className="py-2.5 px-3 text-right">Observed (eq)</th>
                  <th className="py-2.5 px-3 text-right">Baseline Median</th>
                  <th className="py-2.5 px-3 text-right">Robust Z-Score</th>
                  <th className="py-2.5 px-3 text-right">Percentile</th>
                  <th className="py-2.5 px-3 text-center">Classification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262a35]">
                {mockAnomalies.map((a) => (
                  <tr
                    key={a.period}
                    onClick={() => setSelectedAnomaly(a)}
                    className={`cursor-pointer transition-colors ${
                      selectedAnomaly.period === a.period
                        ? 'bg-[#262a35] text-[#ffc174]'
                        : 'bg-[#171b26] hover:bg-[#262a35]/60 text-[#dfe2f1]'
                    }`}
                  >
                    <td className="py-3 px-3 font-bold">{a.period}</td>
                    <td className="py-3 px-3 text-right font-mono font-bold">{a.observed.toLocaleString()}</td>
                    <td className="py-3 px-3 text-right font-mono text-[#a08e7a]">{a.baseline.toLocaleString()}</td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-[#ff938c]">+{a.robustZ}</td>
                    <td className="py-3 px-3 text-right font-mono text-[#7bd0ff]">{a.percentile}%</td>
                    <td className="py-3 px-3 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#93000a]/20 text-[#ffb4ab]">
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Decomposition: Dates & Cells */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Dates Breakdown */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">Excess Attributed by Observation Date</h3>
            <span className="font-caption-mono text-xs text-[#a08e7a] block mb-3">Which dates drove the surge</span>

            <div className="space-y-3 font-caption-mono text-xs">
              {[
                { date: '2024-08-17', excess: 1420, share: 39.2 },
                { date: '2024-08-16', excess: 1180, share: 32.6 },
                { date: '2024-08-18', excess: 780, share: 21.5 },
                { date: '2024-08-15', excess: 240, share: 6.7 },
              ].map((d) => (
                <div key={d.date} className="p-2.5 rounded bg-[#171b26] border border-[#262a35]">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-[#dfe2f1]">{d.date}</span>
                    <span className="text-[#ffc174] font-bold">+{d.excess} eq ({d.share}%)</span>
                  </div>
                  <div className="w-full bg-[#0a0e18] h-2 rounded-full overflow-hidden">
                    <div className="bg-[#f59e0b] h-full rounded-full" style={{ width: `${d.share}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Cells Breakdown */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">Excess Attributed by H3 Hexagon Cell</h3>
            <span className="font-caption-mono text-xs text-[#a08e7a] block mb-3">Which spatial cells drove the surge</span>

            <div className="space-y-3 font-caption-mono text-xs">
              {[
                { cell: '872830828ffffff', name: 'Willamette Ridge Basin', excess: 640, share: 17.7 },
                { cell: '872830829ffffff', name: 'Cedar Flats North', excess: 510, share: 14.1 },
                { cell: '87283082affffff', name: 'Santiam Pass Burn Scar', excess: 420, share: 11.6 },
                { cell: '87283082bffffff', name: 'McKenzie Tributary', excess: 380, share: 10.5 },
              ].map((c) => (
                <div key={c.cell} className="p-2.5 rounded bg-[#171b26] border border-[#262a35]">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-[#dfe2f1]">{c.name}</span>
                    <span className="text-[#7bd0ff] font-bold">+{c.excess} eq ({c.share}%)</span>
                  </div>
                  <div className="w-full bg-[#0a0e18] h-2 rounded-full overflow-hidden">
                    <div className="bg-[#7bd0ff] h-full rounded-full" style={{ width: `${c.share * 2}%` }}></div>
                  </div>
                  <span className="text-[10px] text-[#a08e7a] mt-0.5 block">{c.cell}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

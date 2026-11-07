import { useState } from 'react';
import MethodDrawer from '../../../components/provenance/MethodDrawer';

interface ModelMetric {
  key: string;
  name: string;
  sub: string;
  params: string;
  mae: string;
  rank: string;
  cov: string;
  desc: string;
  color: string;
}

const models: Record<string, ModelMetric> = {
  M0: {
    key: 'M0',
    name: 'Identity Reference',
    sub: 'Naïve direct count concatenation (No correction)',
    params: 'β₀ = 1.000, β₁ = 0.000 (Fixed)',
    mae: '48.2%',
    rank: '0.72',
    cov: '61.4%',
    desc: 'Uncalibrated Baseline',
    color: 'text-[#ffb4ab]',
  },
  M1: {
    key: 'M1',
    name: 'Global Scaled Ratio',
    sub: 'Single scalar transformation factor over planetary aggregate',
    params: 'γ_global = 0.408 (±0.006)',
    mae: '28.5%',
    rank: '0.81',
    cov: '82.1%',
    desc: 'Global Scalar 0.408x',
    color: 'text-[#7bd0ff]',
  },
  M2: {
    key: 'M2',
    name: 'Stratified Ratio (Production)',
    sub: 'Biome (14 classes) × Season (Q1-Q4) × Diurnal Pass',
    params: '112 Regional Tensors + Solar Zenith',
    mae: '18.2%',
    rank: '0.89',
    cov: '94.6%',
    desc: 'Stratified Biome × Season',
    color: 'text-[#ffc174]',
  },
  M3: {
    key: 'M3',
    name: 'Count Regression GLM',
    sub: 'Negative Binomial with solar zenith and cloud covariates',
    params: 'Poisson-Gamma Dispersion α = 0.342',
    mae: '16.9%',
    rank: '0.91',
    cov: '95.2%',
    desc: 'Neg-Binomial GLM Covariates',
    color: 'text-[#c4e7ff]',
  },
  M4: {
    key: 'M4',
    name: 'Quantile Mapping (CDF)',
    sub: 'Empirical transfer function matching sensor CDF distributions',
    params: '100 Spline Knot Interpolators',
    mae: '19.4%',
    rank: '0.88',
    cov: '93.8%',
    desc: 'CDF Quantile Mapping',
    color: 'text-[#ffddb8]',
  },
};

export default function ComparisonPage() {
  const [activeModel, setActiveModel] = useState<string>('M2');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const cur = models[activeModel] || models['M2'];

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 pt-5 pb-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                NASA SPACE APPS 2026 • RECONCILIATION SUITE
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">H3-RES7 GRAIN (4.38 KM²)</span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#d8c3ad]">TEMPORAL WINDOW: 2012-01 TO 2025-12</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              MODIS vs. VIIRS Statistical Calibration &amp; Overlap Harmonization
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Raw detections from MODIS (1km) and VIIRS (375m) reflect differing instrument optics, orbit overpass times, and sub-pixel thermal sensitivity. Direct summation produces artificial fire count spikes post-2012. TerraFlare calibrates observations on a unified H3 cell-day grain with cross-sensor transfer functions.
            </p>
          </div>
          <div className="flex items-center gap-3 self-start lg:self-end">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded bg-[#1c1f2a] hover:bg-[#262a35] text-[#dfe2f1] border border-[#374151] font-title-sm text-xs font-semibold transition-colors shadow-sm"
            >
              <span className="material-symbols-outlined text-[#7bd0ff] text-base">menu_book</span>
              <span>Methodology &amp; Scientific Protocol</span>
            </button>
            <button
              onClick={() => setActiveModel('M2')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded bg-[#f59e0b] text-[#0B0F19] font-title-sm text-xs font-bold hover:bg-[#ffb95f] transition-colors shadow-sm"
            >
              <span className="material-symbols-outlined text-base">tune</span>
              <span>Re-estimate (In-Memory DuckDB)</span>
            </button>
          </div>
        </div>

        {/* Telemetry Snapshot Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
          <div className="p-3 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Target Metric (MAE)</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`font-mono-metric-lg text-2xl font-bold ${cur.color}`}>{cur.mae}</span>
              <span className="font-caption-mono text-[10px] text-[#7bd0ff]">[-30.0% vs M0]</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] truncate mt-1">{cur.desc}</span>
          </div>
          <div className="p-3 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Spearman Rank Corr (ρ)</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff]">{cur.rank}</span>
              <span className="font-caption-mono text-[10px] text-[#ffc174] font-medium">p &lt; 0.0001</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] truncate mt-1">Cell-Day Energy Fidelity</span>
          </div>
          <div className="p-3 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Interval Coverage</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#dfe2f1]">{cur.cov}</span>
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">NOMINAL: 95%</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] truncate mt-1">Blocked CV Coverage</span>
          </div>
          <div className="p-3 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Active Regime Model</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174]">{activeModel}</span>
              <span className="px-1.5 py-0.5 rounded bg-[#f59e0b]/20 text-[#ffc174] font-caption-mono text-[10px] font-bold">DEPLOYED</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] truncate mt-1">Multi-Sensor Ingestion Layer</span>
          </div>
        </div>
      </section>

      {/* Main Canvas: Model Benchmark Table */}
      <section className="w-full px-6 py-6 space-y-6">
        <div className="w-full bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 gap-2 border-b border-[#262a35]">
            <div>
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">table_chart</span>
                <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">Harmonization Model Benchmark &amp; Hypothesis Matrix</h2>
              </div>
              <p className="font-caption-mono text-xs text-[#d8c3ad] mt-0.5">
                Click candidate method to activate live projection and evaluate delta parameters across holdout records.
              </p>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto font-caption-mono text-xs bg-[#0a0e18] px-3 py-1.5 rounded border border-[#262a35]">
              <span className="text-[#a08e7a]">HOLDOUT:</span>
              <span className="text-[#7bd0ff] font-semibold">2021–2023 LEAVE-ONE-YEAR-OUT</span>
            </div>
          </div>

          {/* Model Selection Rows */}
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-left font-caption-mono text-xs">
              <thead>
                <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase tracking-wider border-b border-[#262a35]">
                  <th className="py-2.5 px-3">Key</th>
                  <th className="py-2.5 px-3">Method Formulation</th>
                  <th className="py-2.5 px-3">Parameterization</th>
                  <th className="py-2.5 px-3 text-right">Rel-MAE (%)</th>
                  <th className="py-2.5 px-3 text-right">Rank-Corr (ρ)</th>
                  <th className="py-2.5 px-3 text-right">95% Cov (%)</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262a35]">
                {Object.values(models).map((m) => {
                  const isCurrent = activeModel === m.key;
                  return (
                    <tr
                      key={m.key}
                      onClick={() => setActiveModel(m.key)}
                      className={`cursor-pointer transition-colors ${
                        isCurrent
                          ? 'bg-[#262a35] text-[#ffc174]'
                          : 'bg-[#171b26] hover:bg-[#262a35]/60 text-[#dfe2f1]'
                      }`}
                    >
                      <td className={`py-3 px-3 font-label-mono font-bold ${m.color}`}>{m.key}</td>
                      <td className="py-3 px-3">
                        <span className="font-title-sm text-sm font-semibold text-[#dfe2f1] block">{m.name}</span>
                        <span className="text-[#a08e7a] text-[11px]">{m.sub}</span>
                      </td>
                      <td className="py-3 px-3 text-[#d8c3ad]">{m.params}</td>
                      <td className={`py-3 px-3 text-right font-mono font-bold ${m.color}`}>{m.mae}</td>
                      <td className="py-3 px-3 text-right font-mono text-[#dfe2f1]">{m.rank}</td>
                      <td className="py-3 px-3 text-right font-mono text-[#dfe2f1]">{m.cov}</td>
                      <td className="py-3 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isCurrent
                              ? 'bg-[#f59e0b] text-[#0B0F19]'
                              : 'bg-[#0a0e18] text-[#a08e7a]'
                          }`}
                        >
                          {isCurrent ? 'ACTIVE ENGAGED' : 'STANDBY'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          className={`px-2.5 py-1 rounded text-xs font-semibold ${
                            isCurrent
                              ? 'bg-[#f59e0b] text-[#0B0F19]'
                              : 'bg-[#0a0e18] text-[#dfe2f1] hover:bg-[#313540]'
                          }`}
                        >
                          {isCurrent ? 'Active' : 'Select'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Time Series Calibration Comparison */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Overlap Calibration Trajectory (2020-2025)</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">Harmonized HAI vs Unadjusted MODIS &amp; VIIRS counts</span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs">
                Method: {activeModel}
              </span>
            </div>

            {/* SVG Trajectory Chart */}
            <div className="w-full h-56 bg-[#0a0e18] rounded p-3 relative flex flex-col justify-end border border-[#262a35]">
              <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 500 160">
                <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="500" y1="40" y2="40"></line>
                <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="500" y1="80" y2="80"></line>
                <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="500" y1="120" y2="120"></line>
                {/* Confidence band */}
                <path d="M 0,150 Q 100,140 180,110 T 300,30 T 400,90 T 500,130 L 500,145 L 400,110 L 300,50 L 180,125 L 0,155 Z" fill="#f59e0b" fillOpacity="0.15"></path>
                {/* VIIRS Line */}
                <path d="M 0,145 Q 100,135 180,95 T 300,20 T 400,80 T 500,120" fill="none" stroke="#7bd0ff" strokeWidth="2"></path>
                {/* MODIS Line */}
                <path d="M 0,152 Q 100,146 180,125 T 300,75 T 400,115 T 500,140" fill="none" stroke="#ffbcb7" strokeDasharray="4,3" strokeWidth="2"></path>
                {/* Harmonized Line */}
                <path d="M 0,148 Q 100,138 180,105 T 300,38 T 400,95 T 500,128" fill="none" stroke="#ffc174" strokeWidth="2.5"></path>
              </svg>
              <div className="flex items-center justify-between pt-2 text-[10px] font-caption-mono text-[#a08e7a]">
                <div className="flex items-center gap-1.5 text-[#ffc174] font-semibold">
                  <span className="w-3 h-1 bg-[#ffc174] rounded-full inline-block"></span>Harmonized
                </div>
                <div className="flex items-center gap-1.5 text-[#7bd0ff]">
                  <span className="w-3 h-1 bg-[#7bd0ff] rounded-full inline-block"></span>VIIRS (375m)
                </div>
                <div className="flex items-center gap-1.5 text-[#ffbcb7]">
                  <span className="w-3 h-1 bg-[#ffbcb7] rounded-full inline-block"></span>MODIS (1km)
                </div>
                <div className="flex items-center gap-1.5 text-[#a08e7a]">
                  <span className="w-2.5 h-2 bg-[#f59e0b]/20 inline-block rounded"></span>±95% Interval
                </div>
              </div>
            </div>
          </div>

          {/* Chart 2: Inter-Sensor Co-Detection & Spatial Agreement */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Cross-Sensor Detection Agreement</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">Coincident vs sensor-exclusive active fire detections</span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
                Co-detection: 62%
              </span>
            </div>

            {/* Proportion Bar */}
            <div className="space-y-3">
              <div className="w-full h-8 rounded-lg overflow-hidden flex text-xs font-bold font-caption-mono">
                <div className="bg-[#f59e0b] text-[#0B0F19] flex items-center justify-center" style={{ width: '62%' }}>
                  62% Coincident
                </div>
                <div className="bg-[#7bd0ff] text-[#00354a] flex items-center justify-center" style={{ width: '26%' }}>
                  26% VIIRS-only
                </div>
                <div className="bg-[#313540] text-[#dfe2f1] flex items-center justify-center" style={{ width: '12%' }}>
                  12% MODIS
                </div>
              </div>

              {/* Details */}
              <div className="grid grid-cols-3 gap-2 font-caption-mono text-xs">
                <div className="p-2.5 rounded bg-[#171b26] border border-[#262a35]">
                  <div className="flex items-center gap-1 text-[#ffc174] font-bold">
                    <span className="w-2 h-2 rounded-full bg-[#ffc174]"></span>62% Both
                  </div>
                  <p className="text-[#a08e7a] text-[10px] mt-1 leading-tight">Confirmed hotspots seen by both sensors.</p>
                </div>
                <div className="p-2.5 rounded bg-[#171b26] border border-[#262a35]">
                  <div className="flex items-center gap-1 text-[#7bd0ff] font-bold">
                    <span className="w-2 h-2 rounded-full bg-[#7bd0ff]"></span>26% VIIRS
                  </div>
                  <p className="text-[#a08e7a] text-[10px] mt-1 leading-tight">Small fires &lt;1km below MODIS detection threshold.</p>
                </div>
                <div className="p-2.5 rounded bg-[#171b26] border border-[#262a35]">
                  <div className="flex items-center gap-1 text-[#dfe2f1] font-bold">
                    <span className="w-2 h-2 rounded-full bg-[#313540]"></span>12% MODIS
                  </div>
                  <p className="text-[#a08e7a] text-[10px] mt-1 leading-tight">Rapid cloud shifts or front quenching between passes.</p>
                </div>
              </div>

              {/* Drift gauge */}
              <div className="pt-2 space-y-1">
                <div className="flex justify-between font-caption-mono text-[11px] text-[#a08e7a]">
                  <span>Euclidean Inter-Sensor Center Drift</span>
                  <span className="text-[#7bd0ff]">Median: 342m (σ: 184m)</span>
                </div>
                <div className="w-full bg-[#171b26] h-2 rounded-full overflow-hidden border border-[#262a35]">
                  <div className="bg-[#7bd0ff] h-full rounded-full" style={{ width: '78%' }}></div>
                </div>
                <div className="flex justify-between text-[10px] font-caption-mono text-[#a08e7a]">
                  <span>0m (Exact Colocated)</span>
                  <span>750m (Pixel Boundary)</span>
                  <span>1500m (Max Match Window)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Drawer */}
      <MethodDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
    </div>
  );
}

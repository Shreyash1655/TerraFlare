import { useState } from 'react';

export default function SeasonShiftPage() {
  const [activeTab, setActiveTab] = useState<'shift' | 'memory' | 'anomaly' | 'cluster'>('shift');

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Mandatory Scientific Disclaimer Banner */}
      <div className="w-full px-6 py-2 bg-[#171b26] border-b border-[#262a35]">
        <div className="flex items-start gap-2.5">
          <span className="material-symbols-outlined text-[#ffc174] text-base mt-0.5 shrink-0">verified_user</span>
          <p className="font-caption-mono text-xs text-[#d8c3ad] leading-relaxed">
            <strong className="text-[#ffc174] font-medium">SCIENTIFIC DISCLAIMER:</strong> All intelligence models are descriptive statistical summaries of the harmonized satellite record. No causal climate attribution or wildfire perimeter claims are made. Radiometric FRP signals denote thermal sensor radiative power, subject to orbital sampling cadences and cloud occlusion masks.
          </p>
        </div>
      </div>

      {/* Tiered Engine Navigation Segment */}
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
            <span className="material-symbols-outlined text-base">trending_up</span>
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
            <span className="material-symbols-outlined text-base">memory</span>
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
            <span className="material-symbols-outlined text-base">crisis_alert</span>
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
            <span className="material-symbols-outlined text-base">radar</span>
            <span>Cluster Tracking &amp; Exposure</span>
            <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#a08e7a] font-caption-mono text-[9px] uppercase font-bold ml-1">
              TIER C
            </span>
          </button>
        </div>
      </div>

      {/* MAIN ENGINE CONTENT CONTAINER */}
      <div className="w-full px-6 py-6 flex flex-col gap-6">
        {activeTab === 'shift' && (
          <div className="flex flex-col gap-6">
            {/* Top Stat Matrix: Phenological Milestones */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Milestone 1: Onset */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#7bd0ff] uppercase tracking-wider">PHENOLOGICAL 10% ONSET</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#7bd0ff] font-label-mono text-xs">DAY 162 → 144</span>
                </div>
                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">Season Onset Shift</span>
                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174]">-18.4</span>
                  <span className="font-label-mono text-xs text-[#ffc174] uppercase">days earlier</span>
                </div>
                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    Theil-Sen slope: <span className="text-[#dfe2f1] font-mono">-1.80 d/yr</span><br />
                    95% CI: <span className="text-[#7bd0ff] font-mono">[-2.41, -1.18]</span> • Kendall's τ = -0.58
                  </p>
                </div>
              </div>

              {/* Milestone 2: Peak */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#ffc174] uppercase tracking-wider">MAX RADIOMETRIC FRP PEAK</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#ffc174] font-label-mono text-xs">AUG 22 → AUG 09</span>
                </div>
                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">Season Peak Advancement</span>
                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#f59e0b]">-13.0</span>
                  <span className="font-label-mono text-xs text-[#f59e0b] uppercase">days forward</span>
                </div>
                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    Gaussian kernel: <span className="text-[#dfe2f1] font-mono">σ=7d</span><br />
                    Mean Daily Peak: <span className="text-[#ffc174] font-mono">4,192 MW</span> (+44.1%)
                  </p>
                </div>
              </div>

              {/* Milestone 3: Cessation */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#7bd0ff] uppercase tracking-wider">AUTUMN TRAIL (90%)</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#7bd0ff] font-label-mono text-xs">OCT 03 → OCT 14</span>
                </div>
                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">Season Cessation Lag</span>
                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff]">+11.2</span>
                  <span className="font-label-mono text-xs text-[#7bd0ff] uppercase">days longer</span>
                </div>
                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35]">
                  <p className="font-caption-mono text-[11px] text-[#d8c3ad] leading-tight">
                    Theil-Sen slope: <span className="text-[#dfe2f1] font-mono">+1.12 d/yr</span><br />
                    Late-autumn smoldering: <span className="text-[#7bd0ff] font-mono">p=0.002</span>, Mann-Kendall
                  </p>
                </div>
              </div>

              {/* Milestone 4: Total Window */}
              <div className="bg-[#1c1f2a] border border-[#262a35] p-4 rounded shadow-md relative overflow-hidden flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-caption-mono text-[10px] text-[#ffb4ab] uppercase tracking-wider">ACTIVE DURATION DELTA</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#93000a] text-[#ffdad6] font-label-mono text-xs">CRITICAL EXPANSION</span>
                </div>
                <span className="font-headline-sm text-sm font-bold text-[#dfe2f1]">Total Burning Window</span>
                <div className="my-2 flex items-baseline gap-1.5">
                  <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174]">+29.6</span>
                  <span className="font-label-mono text-xs text-[#ffc174] uppercase">days added</span>
                </div>
                <div className="bg-[#0a0e18] p-2 rounded border border-[#262a35] flex items-center justify-between">
                  <span className="font-label-mono text-xs text-[#dfe2f1] font-bold">114.2 d → 143.8 d</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#f59e0b]/20 text-[#ffc174] font-caption-mono text-[10px] font-bold">p &lt; 0.001</span>
                </div>
              </div>
            </div>

            {/* Sigmoid Phenology Curves Visualization */}
            <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-headline-sm text-base font-bold text-[#dfe2f1]">
                      Cumulative Radiative Energy Sigmoid (DOY 100 - 320)
                    </h3>
                    <span className="px-2 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-[10px] font-semibold">
                      SIGMOID REGRESSION
                    </span>
                  </div>
                  <p className="font-body-sm text-xs text-[#d8c3ad] mt-0.5">
                    Pacific NW Bioregion: Baseline Era (2002–2012) vs Recent Multi-Sensor Era (2015–2025)
                  </p>
                </div>
                <div className="px-3 py-1.5 rounded bg-[#0a0e18] border border-[#262a35] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-base">verified</span>
                  <span className="font-caption-mono text-xs text-[#7bd0ff] font-bold uppercase tracking-wider">
                    STATISTICALLY SIGNIFICANT SHIFT (p &lt; 0.001)
                  </span>
                </div>
              </div>

              {/* Chart Canvas */}
              <div className="w-full bg-[#0a0e18] p-4 rounded border border-[#262a35] relative">
                <div className="absolute top-4 right-4 flex flex-col items-end gap-1 font-caption-mono text-xs pointer-events-none">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-0.5 bg-[#a08e7a] inline-block"></span>
                    <span className="text-[#d8c3ad]">Baseline Era (2002–2012) [MODIS]</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-0.5 bg-[#ffc174] inline-block"></span>
                    <span className="text-[#ffc174] font-bold">Recent Era (2015–2025) [Harmonized]</span>
                  </div>
                </div>

                <svg className="w-full h-72 select-none" preserveAspectRatio="none" viewBox="0 0 800 300">
                  <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="800" y1="75" y2="75"></line>
                  <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="800" y1="150" y2="150"></line>
                  <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="800" y1="225" y2="225"></line>
                  {/* Baseline curve */}
                  <path d="M 0,290 Q 200,285 350,250 T 520,60 T 800,15" fill="none" stroke="#a08e7a" strokeDasharray="5,3" strokeWidth="2"></path>
                  {/* Shifted Recent curve */}
                  <path d="M 0,290 Q 150,280 280,210 T 450,40 T 800,10" fill="none" stroke="#ffc174" strokeWidth="3"></path>
                  {/* 10% Onset line */}
                  <line stroke="#7bd0ff" strokeDasharray="2,2" x1="280" x2="280" y1="0" y2="300"></line>
                  <circle cx="280" cy="210" fill="#7bd0ff" r="5"></circle>
                  {/* 90% Cessation line */}
                  <line stroke="#ff938c" strokeDasharray="2,2" x1="560" x2="560" y1="0" y2="300"></line>
                  <circle cx="560" cy="35" fill="#ff938c" r="5"></circle>
                </svg>

                <div className="flex justify-between font-caption-mono text-xs text-[#a08e7a] pt-2 border-t border-[#262a35]">
                  <span>DOY 100 (APR)</span>
                  <span>DOY 160 (JUN 09 - Onset)</span>
                  <span className="text-[#ffc174] font-bold">DOY 220 (AUG - Max FRP Peak)</span>
                  <span>DOY 285 (OCT - Cessation)</span>
                  <span>DOY 320 (NOV)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'memory' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">Spatial Fire Memory &amp; Reoccurrence Map</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">Classifying H3 cells into persistent, emerging, declining, or sporadic activity</span>
              </div>
              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs font-bold">
                10-YEAR MULTI-SENSOR RECURRENCE
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-3.5 bg-[#171b26] rounded border border-[#262a35]">
                <div className="flex items-center gap-1.5 text-[#ffc174] font-bold font-caption-mono text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ffc174]"></span>Persistent (≥70% Yrs)
                </div>
                <div className="text-xl font-bold font-mono text-[#dfe2f1] mt-1">1,420 cells</div>
                <p className="text-[11px] text-[#a08e7a] mt-1">High annual recurrence with stationary trend.</p>
              </div>
              <div className="p-3.5 bg-[#171b26] rounded border border-[#262a35]">
                <div className="flex items-center gap-1.5 text-[#ff938c] font-bold font-caption-mono text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ff938c]"></span>Emerging Hotspots
                </div>
                <div className="text-xl font-bold font-mono text-[#dfe2f1] mt-1">680 cells</div>
                <p className="text-[11px] text-[#a08e7a] mt-1">Low early recurrence with sharp recent expansion.</p>
              </div>
              <div className="p-3.5 bg-[#171b26] rounded border border-[#262a35]">
                <div className="flex items-center gap-1.5 text-[#7bd0ff] font-bold font-caption-mono text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#7bd0ff]"></span>Declining Activity
                </div>
                <div className="text-xl font-bold font-mono text-[#dfe2f1] mt-1">490 cells</div>
                <p className="text-[11px] text-[#a08e7a] mt-1">Previously active with falling recent detection rates.</p>
              </div>
              <div className="p-3.5 bg-[#171b26] rounded border border-[#262a35]">
                <div className="flex items-center gap-1.5 text-[#dfe2f1] font-bold font-caption-mono text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#313540]"></span>Sporadic Detections
                </div>
                <div className="text-xl font-bold font-mono text-[#dfe2f1] mt-1">3,110 cells</div>
                <p className="text-[11px] text-[#a08e7a] mt-1">Isolated seasonal detections across years.</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'anomaly' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">Explainable Wildfire Anomaly Engine</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">Robust Z-score and MAD excess decomposition by date and cell</span>
              </div>
              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
                ROBUST Z: +3.84 (EXTREME)
              </span>
            </div>
            <div className="p-4 bg-[#0a0e18] rounded border border-[#262a35] font-caption-mono text-xs text-[#dfe2f1]">
              <span className="text-[#ffc174] font-bold">EXPLANATION SUMMARY:</span>
              <p className="mt-1 text-[#d8c3ad] leading-relaxed">
                Activity in the selected target period (2024-W33) was 3.84 times the historical baseline median (2000–2023). 14 spatial cells accounted for 74.2% of the total radiative excess, driven primarily by intense thermal detections recorded on August 16–18.
              </p>
            </div>
          </div>
        )}

        {activeTab === 'cluster' && (
          <div className="bg-[#1c1f2a] border border-[#262a35] p-5 rounded-lg shadow-md flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
              <div>
                <h3 className="font-title-md text-base font-bold text-[#dfe2f1]">Activity Episode Clustering &amp; Exposure</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">DBSCAN spatiotemporal clustering with asset proximity buffers</span>
              </div>
              <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#a08e7a] font-caption-mono text-xs">
                EPS: 1.5 KM • MIN SAMPLES: 8
              </span>
            </div>
            <p className="font-body-sm text-xs text-[#d8c3ad]">
              Clusters represent spatiotemporally grouped active fire detections (activity episodes), not verified burn perimeters. Exposure metrics denote geographical proximity within configured buffer zones (1km, 5km, 10km).
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

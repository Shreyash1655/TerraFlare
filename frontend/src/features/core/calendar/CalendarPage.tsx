import { useState } from 'react';

const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

export default function CalendarPage() {
  const [selectedYear, setSelectedYear] = useState('2026');
  const [selectedMetric, setSelectedMetric] = useState<'hai' | 'frp'>('hai');
  const [hoveredDay, setHoveredDay] = useState<{ date: string; value: number; lower: number; upper: number } | null>({
    date: '2024-08-18',
    value: 512,
    lower: 488,
    upper: 540,
  });

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Telemetry & Control Band */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div className="flex flex-col max-w-3xl">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-[#f59e0b] animate-pulse"></span>
              <span className="font-label-mono text-[10px] text-[#ffc174] uppercase tracking-widest font-semibold">
                MISSION TELEMETRY • SUBSYSTEM 03
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">| BASELINE 2000-2026 UTC</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Historical Burning Activity Calendar &amp; Multi-Year Climatology Matrix
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] mt-1 leading-relaxed">
              Sensor-calibrated daily thermal radiance metrics, cross-era sensor harmonization confidence intervals, and longitudinal seasonal wildfire anomaly tracking.
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center gap-2 bg-[#171b26] p-1.5 rounded-lg border border-[#262a35] shadow-sm">
            {/* Region */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c1f2a] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#7bd0ff] text-sm">travel_explore</span>
              <select className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer">
                <option className="bg-[#1c1f2a]" value="pwn">Pacific NW / Boreal Cascadia</option>
                <option className="bg-[#1c1f2a]" value="amz">Amazon Basin Arc</option>
                <option className="bg-[#1c1f2a]" value="sib">Siberian Larch Taiga</option>
                <option className="bg-[#1c1f2a]" value="aus">SE Australia Eurobodalla</option>
              </select>
            </div>

            {/* Target Year */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c1f2a] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#ffc174] text-sm">history_edu</span>
              <label className="font-caption-mono text-[10px] text-[#a08e7a]">YEAR:</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                className="bg-transparent font-label-mono text-xs text-[#ffc174] font-semibold focus:outline-none cursor-pointer"
              >
                <option className="bg-[#1c1f2a]" value="2026">2026 (YTD)</option>
                <option className="bg-[#1c1f2a]" value="2025">2025</option>
                <option className="bg-[#1c1f2a]" value="2024">2024</option>
                <option className="bg-[#1c1f2a]" value="2023">2023</option>
                <option className="bg-[#1c1f2a]" value="2020">2020</option>
                <option className="bg-[#1c1f2a]" value="2012">2012 (Sensor Transition)</option>
                <option className="bg-[#1c1f2a]" value="2003">2003 (Early MODIS)</option>
              </select>
            </div>

            {/* Metric Toggle */}
            <div className="flex items-center bg-[#1c1f2a] p-0.5 rounded border border-[#262a35]">
              <button
                onClick={() => setSelectedMetric('hai')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedMetric === 'hai'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Harmonized HAI
              </button>
              <button
                onClick={() => setSelectedMetric('frp')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedMetric === 'frp'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                FRP (MW)
              </button>
            </div>
          </div>
        </div>

        {/* 4 Quick Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-5">
          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Annual Harmonized Total</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174]">142,890</span>
              <span className="font-caption-mono text-[10px] text-[#7bd0ff]">±3.2%</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">+14.2% vs 10-Yr Climatology</span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Climatological Peak Day</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#dfe2f1]">Aug 18</span>
              <span className="font-caption-mono text-[10px] text-[#ffc174]">DOY 231</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">Peak Daily Density: 512 eq</span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Current vs Median</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff]">1.34x</span>
              <span className="font-caption-mono text-[10px] text-[#ffbcb7]">Q3 Tier</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">Historical IQR: 280–420 eq</span>
          </div>

          <div className="p-3.5 rounded bg-[#171b26] border border-[#262a35] flex flex-col justify-between">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Fire Season Length</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-mono-metric-lg text-2xl font-bold text-[#ffddb8]">118 Days</span>
              <span className="font-caption-mono text-[10px] text-[#ffb4ab]">+18d Exp</span>
            </div>
            <span className="font-caption-mono text-[10px] text-[#d8c3ad] mt-1">10% Onset to 90% Cessation</span>
          </div>
        </div>
      </section>

      {/* Main Calendar Matrix & Heatmap */}
      <section className="w-full px-6 py-6 space-y-6">
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#262a35] gap-2">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1] flex items-center gap-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">calendar_month</span>
                Daily Burning Activity Heatmap ({selectedYear})
              </h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">
                365-Day Matrix showing Harmonized Fire Activity Index with uncertainty intervals
              </span>
            </div>

            {/* Hovered Day Telemetry Box */}
            {hoveredDay && (
              <div className="flex items-center gap-3 bg-[#0a0e18] px-3.5 py-1.5 rounded border border-[#262a35] font-caption-mono text-xs">
                <span className="text-[#a08e7a] font-semibold">{hoveredDay.date}:</span>
                <span className="text-[#ffc174] font-bold">{hoveredDay.value} eq</span>
                <span className="text-[#d8c3ad]">[{hoveredDay.lower} – {hoveredDay.upper}]</span>
              </div>
            )}
          </div>

          {/* Simulated 12-Month Heatmap Calendar Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-4">
            {months.map((m, mIdx) => {
              // Simulated intensity per month
              const isPeak = mIdx >= 6 && mIdx <= 8;
              const isModerate = mIdx === 5 || mIdx === 9;
              return (
                <div key={m} className="bg-[#171b26] p-3 rounded border border-[#262a35]">
                  <div className="flex justify-between items-center mb-2 font-caption-mono text-xs">
                    <span className="font-bold text-[#dfe2f1]">{m}</span>
                    <span className="text-[#a08e7a]">
                      {isPeak ? 'High Activity' : isModerate ? 'Moderate' : 'Low / Quiescent'}
                    </span>
                  </div>
                  {/* Days grid 4x7 or 5x7 */}
                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: 30 }).map((_, dIdx) => {
                      let cellBg = 'bg-[#0a0e18]';
                      let cellVal = Math.floor(Math.random() * 20) + 1;
                      if (isPeak) {
                        cellBg = dIdx % 3 === 0 ? 'bg-[#f59e0b]' : 'bg-[#ffc174]/80';
                        cellVal = Math.floor(Math.random() * 300) + 200;
                      } else if (isModerate) {
                        cellBg = dIdx % 2 === 0 ? 'bg-[#7bd0ff]/60' : 'bg-[#1c1f2a]';
                        cellVal = Math.floor(Math.random() * 80) + 30;
                      }
                      return (
                        <div
                          key={dIdx}
                          onMouseEnter={() =>
                            setHoveredDay({
                              date: `${selectedYear}-${String(mIdx + 1).padStart(2, '0')}-${String(dIdx + 1).padStart(2, '0')}`,
                              value: cellVal,
                              lower: Math.round(cellVal * 0.92),
                              upper: Math.round(cellVal * 1.08),
                            })
                          }
                          className={`w-full aspect-square rounded-sm ${cellBg} hover:ring-2 hover:ring-[#7bd0ff] cursor-pointer transition-all`}
                        ></div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Color scale legend */}
          <div className="flex items-center justify-between pt-4 mt-3 border-t border-[#262a35] font-caption-mono text-xs text-[#a08e7a]">
            <span>Low (0 detections)</span>
            <div className="flex items-center gap-1">
              <span className="w-4 h-3 bg-[#0a0e18] rounded-xs border border-[#262a35]"></span>
              <span className="w-4 h-3 bg-[#1c1f2a] rounded-xs"></span>
              <span className="w-4 h-3 bg-[#7bd0ff]/60 rounded-xs"></span>
              <span className="w-4 h-3 bg-[#ffc174]/80 rounded-xs"></span>
              <span className="w-4 h-3 bg-[#f59e0b] rounded-xs"></span>
            </div>
            <span>Critical (&gt;400 eq/day)</span>
          </div>
        </div>

        {/* Current Month vs Historical Median */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35]">
            <div>
              <h3 className="font-title-sm text-base font-bold text-[#dfe2f1]">Current Month vs Historical Median</h3>
              <span className="font-caption-mono text-xs text-[#a08e7a]">Comparing current burn activity against 2000–2025 climatological baseline</span>
            </div>
            <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
              AUGUST • PEAK WINDOW
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
            <div className="space-y-3">
              <div className="flex justify-between font-caption-mono text-xs">
                <span className="text-[#a08e7a]">Historical Median:</span>
                <span className="text-[#dfe2f1] font-bold">342 eq</span>
              </div>
              <div className="flex justify-between font-caption-mono text-xs">
                <span className="text-[#a08e7a]">Interquartile Range (IQR):</span>
                <span className="text-[#7bd0ff] font-bold">[240 – 480 eq]</span>
              </div>
              <div className="flex justify-between font-caption-mono text-xs">
                <span className="text-[#a08e7a]">Current Observed Harmonized:</span>
                <span className="text-[#ffc174] font-bold">512 eq (+49.7%)</span>
              </div>
            </div>

            <div className="lg:col-span-2 flex flex-col justify-center space-y-2">
              <div className="relative w-full h-8 bg-[#0a0e18] rounded-lg border border-[#262a35] overflow-hidden flex items-center">
                {/* IQR shaded band */}
                <div className="absolute left-[35%] w-[35%] h-full bg-[#7bd0ff]/20 border-x border-[#7bd0ff]/40"></div>
                {/* Median marker */}
                <div className="absolute left-[50%] h-full w-0.5 bg-[#dfe2f1] z-10"></div>
                {/* Current marker */}
                <div className="absolute left-[72%] h-full w-2 bg-[#ffc174] z-20 rounded shadow"></div>
              </div>
              <div className="flex justify-between font-caption-mono text-[10px] text-[#a08e7a]">
                <span>0 eq (Min)</span>
                <span>Q1 (240)</span>
                <span className="text-[#dfe2f1]">Median (342)</span>
                <span>Q3 (480)</span>
                <span className="text-[#ffc174] font-bold">Current (512)</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

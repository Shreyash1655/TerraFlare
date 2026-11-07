import { useState } from 'react';
import ExportButton from '../export/ExportButton';

const yearsData = [
  { year: 2018, harmonized: 118400, modis: 42100, viirs: 98000, ci: [112000, 124000], sensorMix: 'MODIS + VIIRS' },
  { year: 2019, harmonized: 122100, modis: 43500, viirs: 101200, ci: [116000, 128000], sensorMix: 'MODIS + VIIRS' },
  { year: 2020, harmonized: 148900, modis: 49800, viirs: 124500, ci: [141000, 156000], sensorMix: 'MODIS + VIIRS' },
  { year: 2021, harmonized: 154200, modis: 51200, viirs: 129800, ci: [146000, 162000], sensorMix: 'MODIS + VIIRS' },
  { year: 2022, harmonized: 124500, modis: 41800, viirs: 99400, ci: [118000, 131000], sensorMix: 'MODIS + VIIRS' },
  { year: 2023, harmonized: 148900, modis: 49500, viirs: 121000, ci: [141000, 156000], sensorMix: 'MODIS + VIIRS' },
  { year: 2024, harmonized: 158400, modis: 52100, viirs: 132400, ci: [150000, 166000], sensorMix: 'MODIS + VIIRS' },
  { year: 2025, harmonized: 142890, modis: 48320, viirs: 118450, ci: [138770, 147010], sensorMix: 'MODIS + VIIRS' },
];

export default function HistoryPage() {
  const [selectedRegion, setSelectedRegion] = useState('pwn');
  const [selectedSensorView, setSelectedSensorView] = useState<'harmonized' | 'all'>('harmonized');

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Telemetry Header */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                LONGITUDINAL CLIMATOLOGY
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#ffc174]">2000–2025 HARMONIZED TIME SERIES</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Historical Year-Wise &amp; Month-Wise Analysis
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Long-term annual totals and year-by-month matrices on a unified scale. Raw satellite observations are reconciled across the 2012 constellation transition (from single-sensor MODIS Aqua/Terra to dual MODIS + VIIRS).
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportButton dataset="monthly" regionId={selectedRegion} />
          </div>
        </div>

        {/* Filter Strip */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-5 border-t border-[#262a35] mt-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35]">
              <span className="material-symbols-outlined text-[#7bd0ff] text-sm">location_on</span>
              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              >
                <option className="bg-[#171b26]" value="pwn">Western North America (PacNW)</option>
                <option className="bg-[#171b26]" value="amz">Amazon Basin Arc</option>
                <option className="bg-[#171b26]" value="sib">Siberian Boreal Zone</option>
                <option className="bg-[#171b26]" value="aus">SE Australia Eurobodalla</option>
              </select>
            </div>

            <div className="flex items-center bg-[#171b26] p-0.5 rounded border border-[#262a35]">
              <button
                onClick={() => setSelectedSensorView('harmonized')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedSensorView === 'harmonized'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Harmonized Index (HAI)
              </button>
              <button
                onClick={() => setSelectedSensorView('all')}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedSensorView === 'all'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                Sensor Decomposition
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 font-caption-mono text-xs text-[#a08e7a]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]"></span>
            <span>Sensor Mix: Calibrated Post-2012</span>
          </div>
        </div>
      </section>

      {/* Main Analysis Bento Grid */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Annual Totals Bar Chart */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">Annual Harmonized Activity (2018–2025)</h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">Total calibrated thermal energy equivalent per calendar year with 95% bootstrap intervals</span>
            </div>
            <span className="px-2.5 py-1 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
              MEAN: 139,800 eq/yr
            </span>
          </div>

          {/* SVG Bar Chart */}
          <div className="w-full h-64 bg-[#0a0e18] rounded p-4 relative flex flex-col justify-end border border-[#262a35]">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 600 200">
              <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="600" y1="50" y2="50"></line>
              <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="600" y1="100" y2="100"></line>
              <line stroke="#262a35" strokeDasharray="3,3" x1="0" x2="600" y1="150" y2="150"></line>

              {yearsData.map((y, idx) => {
                const x = 30 + idx * 70;
                const barHeight = (y.harmonized / 180000) * 160;
                const yPos = 180 - barHeight;

                return (
                  <g key={y.year}>
                    {/* Error bar */}
                    <line
                      stroke="#ffc174"
                      strokeWidth="1.5"
                      x1={x + 18}
                      x2={x + 18}
                      y1={180 - (y.ci[1] / 180000) * 160}
                      y2={180 - (y.ci[0] / 180000) * 160}
                    ></line>
                    {/* Bar */}
                    <rect
                      x={x}
                      y={yPos}
                      width="36"
                      height={barHeight}
                      rx="2"
                      fill="#f59e0b"
                      opacity="0.85"
                      className="hover:opacity-100 transition-opacity cursor-pointer"
                    ></rect>
                    {/* Year Label */}
                    <text x={x + 6} y="196" fill="#a08e7a" fontSize="10" fontFamily="JetBrains Mono">
                      {y.year}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="flex items-center justify-between pt-3 font-caption-mono text-xs text-[#a08e7a]">
            <span>Baseline Period: 2002–2020</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-[#ffc174]">
                <span className="w-3 h-3 rounded-xs bg-[#f59e0b] inline-block"></span>Harmonized Total
              </span>
              <span className="flex items-center gap-1.5 text-[#a08e7a]">
                <span className="w-2 h-0.5 bg-[#ffc174] inline-block"></span>95% Bootstrap Range
              </span>
            </div>
          </div>
        </div>

        {/* Year-by-Month Climatological Matrix */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1]">Year × Month Radiance Climatology Heatmap</h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">Monthly aggregated harmonized thermal activity across years</span>
            </div>
            <span className="font-caption-mono text-xs text-[#7bd0ff]">PEAK AUGUST SURGE VISIBLE</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center font-caption-mono text-xs border-collapse">
              <thead>
                <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase">
                  <th className="py-2 px-3 text-left">Year</th>
                  {['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'].map((m, i) => (
                    <th key={i} className="py-2 px-2.5">{m}</th>
                  ))}
                  <th className="py-2 px-3 text-right">Annual Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262a35]">
                {yearsData.map((row) => (
                  <tr key={row.year} className="bg-[#171b26] hover:bg-[#262a35]/60 transition-colors">
                    <td className="py-2.5 px-3 text-left font-bold text-[#dfe2f1]">{row.year}</td>
                    {Array.from({ length: 12 }).map((_, mIdx) => {
                      const isAugust = mIdx === 7;
                      const isSummer = mIdx >= 5 && mIdx <= 8;
                      const cellBg = isAugust ? 'bg-[#f59e0b] text-[#0B0F19] font-bold' : isSummer ? 'bg-[#ffc174]/40 text-[#dfe2f1]' : 'text-[#a08e7a]';
                      const val = isAugust ? '48.2k' : isSummer ? '14.1k' : '1.2k';
                      return (
                        <td key={mIdx} className="py-2 px-1">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] ${cellBg}`}>
                            {val}
                          </span>
                        </td>
                      );
                    })}
                    <td className="py-2.5 px-3 text-right font-bold text-[#ffc174] font-mono">
                      {row.harmonized.toLocaleString()} eq
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

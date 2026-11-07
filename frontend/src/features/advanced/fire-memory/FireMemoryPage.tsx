import { useState } from 'react';

const mockCells = [
  { h3: '872830828ffffff', name: 'Willamette Ridge Basin', recurrence: 0.85, yearsActive: 17, totalYears: 20, slope: '+0.12 d/yr', status: 'persistent' },
  { h3: '872830829ffffff', name: 'Cedar Flats North', recurrence: 0.45, yearsActive: 9, totalYears: 20, slope: '+0.44 d/yr', status: 'emerging' },
  { h3: '87283082affffff', name: 'Santiam Pass Burn Scar', recurrence: 0.50, yearsActive: 10, totalYears: 20, slope: '-0.32 d/yr', status: 'declining' },
  { h3: '87283082bffffff', name: 'McKenzie River Tributary', recurrence: 0.20, yearsActive: 4, totalYears: 20, slope: '+0.01 d/yr', status: 'sporadic' },
];

export default function FireMemoryPage() {
  const [selectedClass, setSelectedClass] = useState<string>('all');
  const [inspectedCell, setInspectedCell] = useState(mockCells[0]);

  const filteredCells = selectedClass === 'all' ? mockCells : mockCells.filter((c) => c.status === selectedClass);

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Header */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER B INTEL • SUBSYSTEM 05
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#ffc174]">20-YEAR H3 SPATIAL RECURRENCE</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Spatial Fire Memory &amp; Historical Reoccurrence Map
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Identifies H3 hexagon cells with multi-year recurring active fire hotspots. Classifies geographic locations as persistent, emerging, declining, or sporadic based on Theil-Sen trend slope and presence ratio.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#7bd0ff]">
              H3 Res 7 • 4.38 km² Grid Cells
            </span>
          </div>
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#f59e0b] text-base">info</span>
          <span>
            <strong className="text-[#dfe2f1]">SCIENTIFIC CONSTRAINTS:</strong> Recurrence indicates satellite detections occurred in multiple calendar years. It does not mean the same physical fire burned continuously across seasons.
          </span>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Classification Filter Tabs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <button
            onClick={() => setSelectedClass('persistent')}
            className={`p-4 rounded border text-left transition-all ${
              selectedClass === 'persistent' ? 'bg-[#262a35] border-[#ffc174]' : 'bg-[#1c1f2a] border-[#262a35]'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-caption-mono text-[10px] text-[#ffc174] uppercase font-bold">PERSISTENT (≥70% YRS)</span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#ffc174]"></span>
            </div>
            <div className="text-2xl font-bold font-mono text-[#dfe2f1]">1,420 cells</div>
            <p className="text-[11px] text-[#a08e7a] mt-1">High recurrence with stationary long-term trend.</p>
          </button>

          <button
            onClick={() => setSelectedClass('emerging')}
            className={`p-4 rounded border text-left transition-all ${
              selectedClass === 'emerging' ? 'bg-[#262a35] border-[#ff938c]' : 'bg-[#1c1f2a] border-[#262a35]'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-caption-mono text-[10px] text-[#ff938c] uppercase font-bold">EMERGING HOTSPOTS</span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#ff938c]"></span>
            </div>
            <div className="text-2xl font-bold font-mono text-[#dfe2f1]">680 cells</div>
            <p className="text-[11px] text-[#a08e7a] mt-1">Low early recurrence with sharp positive trend slope.</p>
          </button>

          <button
            onClick={() => setSelectedClass('declining')}
            className={`p-4 rounded border text-left transition-all ${
              selectedClass === 'declining' ? 'bg-[#262a35] border-[#7bd0ff]' : 'bg-[#1c1f2a] border-[#262a35]'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-caption-mono text-[10px] text-[#7bd0ff] uppercase font-bold">DECLINING ACTIVITY</span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#7bd0ff]"></span>
            </div>
            <div className="text-2xl font-bold font-mono text-[#dfe2f1]">490 cells</div>
            <p className="text-[11px] text-[#a08e7a] mt-1">Historically active cells with falling recent activity.</p>
          </button>

          <button
            onClick={() => setSelectedClass('all')}
            className={`p-4 rounded border text-left transition-all ${
              selectedClass === 'all' ? 'bg-[#262a35] border-[#dfe2f1]' : 'bg-[#1c1f2a] border-[#262a35]'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase font-bold">ALL OBSERVED CELLS</span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#313540]"></span>
            </div>
            <div className="text-2xl font-bold font-mono text-[#dfe2f1]">5,700 cells</div>
            <p className="text-[11px] text-[#a08e7a] mt-1">Full 20-year domain hexagonal spatial footprint.</p>
          </button>
        </div>

        {/* Spatial Recurrence Table & Timeline Drilldown */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Table (7 cols) */}
          <div className="lg:col-span-7 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-3">Reoccurrence Ranked Cells</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-caption-mono text-xs">
                <thead>
                  <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                    <th className="py-2.5 px-3">H3 Index</th>
                    <th className="py-2.5 px-3">Location Descriptor</th>
                    <th className="py-2.5 px-3 text-right">Recurrence</th>
                    <th className="py-2.5 px-3 text-right">Theil-Sen Trend</th>
                    <th className="py-2.5 px-3 text-center">Class</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#262a35]">
                  {filteredCells.map((c) => (
                    <tr
                      key={c.h3}
                      onClick={() => setInspectedCell(c)}
                      className={`cursor-pointer transition-colors ${
                        inspectedCell.h3 === c.h3 ? 'bg-[#262a35] text-[#ffc174]' : 'bg-[#171b26] hover:bg-[#262a35]/60 text-[#dfe2f1]'
                      }`}
                    >
                      <td className="py-3 px-3 font-mono font-bold">{c.h3}</td>
                      <td className="py-3 px-3">{c.name}</td>
                      <td className="py-3 px-3 text-right font-mono font-bold">{(c.recurrence * 100).toFixed(0)}%</td>
                      <td className="py-3 px-3 text-right font-mono text-[#7bd0ff]">{c.slope}</td>
                      <td className="py-3 px-3 text-center">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#0a0e18] text-[#ffc174]">
                          {c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Timeline Drilldown (5 cols) */}
          <div className="lg:col-span-5 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-3">
                <span className="font-caption-mono text-xs text-[#7bd0ff] font-bold">CELL LONGITUDINAL TIMELINE</span>
                <span className="font-mono text-xs text-[#a08e7a]">{inspectedCell.h3}</span>
              </div>
              <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1]">{inspectedCell.name}</h4>
              <p className="font-caption-mono text-xs text-[#a08e7a] mt-0.5">
                Active in {inspectedCell.yearsActive} of {inspectedCell.totalYears} observable satellite years.
              </p>

              {/* Annual Sparkline Bars */}
              <div className="mt-6 space-y-2 font-caption-mono text-xs">
                {[
                  { year: 2021, val: 310, status: 'Active' },
                  { year: 2022, val: 195, status: 'Active' },
                  { year: 2023, val: 412, status: 'Peak' },
                  { year: 2024, val: 395, status: 'Active' },
                  { year: 2025, val: 310, status: 'Active' },
                ].map((item) => (
                  <div key={item.year} className="flex items-center gap-3">
                    <span className="w-12 text-[#a08e7a]">{item.year}</span>
                    <div className="flex-1 h-3.5 bg-[#0a0e18] rounded overflow-hidden">
                      <div
                        className="h-full bg-[#f59e0b] rounded"
                        style={{ width: `${(item.val / 500) * 100}%` }}
                      ></div>
                    </div>
                    <span className="w-16 text-right font-mono text-[#dfe2f1] font-bold">{item.val} eq</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 pt-3 border-t border-[#262a35] flex justify-between font-caption-mono text-xs text-[#a08e7a]">
              <span>Classification: <strong className="text-[#ffc174] uppercase">{inspectedCell.status}</strong></span>
              <span>Slope: <strong className="text-[#7bd0ff]">{inspectedCell.slope}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';

const mockEvents = [
  {
    id: 'EP-2024-PACNW-042',
    name: 'Cedar Creek Thermal Complex',
    first: '2024-08-14 18:22 UTC',
    last: '2024-08-28 04:15 UTC',
    duration: '13.4 days',
    detections: 1420,
    sensors: 'VIIRS (71%) • MODIS (29%)',
    centroid: '44.12°N, -121.85°W',
    maxFrp: '540 MW',
    totalFRP: '18,420 MW-days',
  },
  {
    id: 'EP-2024-PACNW-043',
    name: 'Santiam Ridge Flash Outbreak',
    first: '2024-08-16 12:05 UTC',
    last: '2024-08-22 21:40 UTC',
    duration: '6.4 days',
    detections: 480,
    sensors: 'VIIRS (88%) • MODIS (12%)',
    centroid: '44.38°N, -121.52°W',
    maxFrp: '210 MW',
    totalFRP: '4,120 MW-days',
  },
];

export default function EventsPage() {
  const [selectedEvent, setSelectedEvent] = useState(mockEvents[0]);

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER C INTEL • SUBSYSTEM 07
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">SPATIOTEMPORAL DBSCAN CLUSTERING</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Fire Event Intelligence &amp; Episode Tracking
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Groups nearby active-fire detections across space and time into activity episodes. Aggregates multi-day centroid movement, duration, detection count by sensor, and FRP radiative energy trajectory.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#a08e7a]">
              Parameters: ε = 1.5km • Min Samples = 8
            </span>
          </div>
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">warning</span>
          <span>
            <strong className="text-[#dfe2f1]">SCIENTIFIC CONSTRAINTS:</strong> An activity episode represents a clustered collection of satellite detections, not a verified wildfire perimeter. The footprint bounds the observed sensor points, not the physical burned area.
          </span>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Episodes List & Detail Frame */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* List (6 cols) */}
          <div className="lg:col-span-6 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-3">Clustered Activity Episodes</h3>
            <div className="space-y-3">
              {mockEvents.map((ev) => (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEvent(ev)}
                  className={`p-4 rounded border transition-all cursor-pointer ${
                    selectedEvent.id === ev.id
                      ? 'bg-[#262a35] border-[#ffc174] shadow-md ring-1 ring-[#ffc174]'
                      : 'bg-[#171b26] border-[#262a35] hover:bg-[#262a35]/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-caption-mono text-[10px] text-[#7bd0ff] font-bold">{ev.id}</span>
                    <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-[10px] font-bold">
                      {ev.duration}
                    </span>
                  </div>
                  <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-2">{ev.name}</h4>

                  <div className="grid grid-cols-2 gap-2 bg-[#0a0e18] p-2 rounded font-caption-mono text-xs">
                    <div>
                      <span className="text-[#a08e7a] text-[10px] block">TOTAL DETECTIONS</span>
                      <span className="text-[#dfe2f1] font-bold">{ev.detections} spots</span>
                    </div>
                    <div>
                      <span className="text-[#a08e7a] text-[10px] block">MAX FRP POWER</span>
                      <span className="text-[#ffbcb7] font-bold">{ev.maxFrp}</span>
                    </div>
                  </div>
                  <div className="mt-2 text-[11px] font-caption-mono text-[#a08e7a]">
                    Sensors: <span className="text-[#dfe2f1]">{ev.sensors}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Episode Telemetry Inspector (6 cols) */}
          <div className="lg:col-span-6 bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4">
                <div>
                  <span className="font-caption-mono text-xs text-[#ffc174] font-bold">EPISODE INSPECTOR</span>
                  <h4 className="font-title-sm text-base font-bold text-[#dfe2f1] mt-0.5">{selectedEvent.name}</h4>
                </div>
                <span className="font-mono text-xs text-[#a08e7a]">{selectedEvent.centroid}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4 font-caption-mono text-xs">
                <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                  <span className="text-[#a08e7a] block text-[10px]">FIRST DETECTION (UTC)</span>
                  <span className="text-[#dfe2f1] font-bold mt-0.5 block">{selectedEvent.first}</span>
                </div>
                <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                  <span className="text-[#a08e7a] block text-[10px]">LAST DETECTION (UTC)</span>
                  <span className="text-[#dfe2f1] font-bold mt-0.5 block">{selectedEvent.last}</span>
                </div>
              </div>

              {/* Daily FRP Trajectory Simulation */}
              <h5 className="font-title-sm text-xs font-bold text-[#dfe2f1] mb-2">Daily FRP Radiative Power Flux (MW)</h5>
              <div className="space-y-2 font-caption-mono text-xs">
                {[
                  { date: 'Aug 15', spots: 120, frp: 840 },
                  { date: 'Aug 16', spots: 340, frp: 2450 },
                  { date: 'Aug 17', spots: 512, frp: 4192 },
                  { date: 'Aug 18', spots: 448, frp: 3620 },
                ].map((d) => (
                  <div key={d.date} className="p-2.5 rounded bg-[#0a0e18] border border-[#262a35] flex items-center justify-between">
                    <span className="font-bold text-[#dfe2f1]">{d.date}</span>
                    <span className="text-[#a08e7a]">{d.spots} detections</span>
                    <span className="font-bold text-[#ffc174] font-mono">{d.frp} MW</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 pt-3 border-t border-[#262a35] flex justify-between font-caption-mono text-xs text-[#a08e7a]">
              <span>Cumulative FRP: <strong className="text-[#ffc174]">{selectedEvent.totalFRP}</strong></span>
              <span>Footprint: Convex Hull Polygon</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

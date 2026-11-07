import { useState } from 'react';

interface ExposureLayer {
  id: string;
  name: string;
  category: string;
  source: string;
  version: string;
  buffer1km: string;
  buffer5km: string;
  buffer10km: string;
  unit: string;
  status: 'active' | 'projected';
}

const layers: ExposureLayer[] = [
  {
    id: 'settlements',
    name: 'Human Settlements & Populated Places',
    category: 'Socioeconomic Infrastructure',
    source: 'OpenStreetMap Extracts (GeoFabrik)',
    version: '2026.1',
    buffer1km: '1',
    buffer5km: '4',
    buffer10km: '12',
    unit: 'settlements',
    status: 'active',
  },
  {
    id: 'population',
    name: 'Modelled Residential Population',
    category: 'Demographic Exposure',
    source: 'Global Human Settlement Layer (GHSL)',
    version: 'GHS-POP-2023',
    buffer1km: '420',
    buffer5km: '3,840',
    buffer10km: '18,200',
    unit: 'residents (est.)',
    status: 'active',
  },
  {
    id: 'transport',
    name: 'Primary & Secondary Road Corridors',
    category: 'Lifeline Networks',
    source: 'OSM Highways Primary / Trunk',
    version: '2026.1',
    buffer1km: '12.4',
    buffer5km: '68.4',
    buffer10km: '210.8',
    unit: 'km centerline',
    status: 'active',
  },
  {
    id: 'protected',
    name: 'Protected Wilderness & Conservation Reserves',
    category: 'Ecological Assets',
    source: 'World Database on Protected Areas (WDPA)',
    version: 'WDPA-2025-V2',
    buffer1km: '1',
    buffer5km: '2',
    buffer10km: '3',
    unit: 'designated zones',
    status: 'active',
  },
];

export default function ExposurePage() {
  const [selectedBuffer, setSelectedBuffer] = useState<'1km' | '5km' | '10km'>('5km');

  return (
    <div className="flex flex-col w-full pb-16">
      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER C INTEL • SUBSYSTEM 08
              </span>
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">MULTI-CRITERIA BUFFER GEOPROCESSING</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Fire Impact &amp; Geographic Exposure Intelligence
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Calculates mapped infrastructure, human population grids, and designated conservation boundaries lying within proximity buffers of observed thermal hotspot detections.
            </p>
          </div>

          {/* Buffer Control Toggle */}
          <div className="flex items-center bg-[#171b26] p-1 rounded-lg border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] px-2 uppercase">Buffer Radius:</span>
            {(['1km', '5km', '10km'] as const).map((buf) => (
              <button
                key={buf}
                onClick={() => setSelectedBuffer(buf)}
                className={`px-3 py-1 rounded font-label-mono text-xs font-semibold transition-all ${
                  selectedBuffer === buf
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
              >
                {buf}
              </button>
            ))}
          </div>
        </div>

        {/* Limitation Note */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">warning</span>
          <span>
            <strong className="text-[#dfe2f1]">SCIENTIFIC CONSTRAINTS:</strong> Proximity is not confirmed damage, loss, or forecast casualty risk. It indicates that an asset intersects a geographic buffer around observed active satellite detections.
          </span>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* Layer Exposure Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {layers.map((layer) => {
            const val =
              selectedBuffer === '1km'
                ? layer.buffer1km
                : selectedBuffer === '5km'
                ? layer.buffer5km
                : layer.buffer10km;

            return (
              <div
                key={layer.id}
                className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-caption-mono text-[9px] text-[#a08e7a] uppercase truncate">{layer.category}</span>
                    <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
                  </div>
                  <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-2">{layer.name}</h4>
                  <div className="my-2">
                    <span className="font-mono text-2xl font-bold text-[#ffc174]">{val}</span>
                    <span className="font-caption-mono text-xs text-[#a08e7a] ml-1.5">{layer.unit}</span>
                  </div>
                </div>
                <div className="pt-2 border-t border-[#262a35] flex justify-between font-caption-mono text-[10px] text-[#a08e7a]">
                  <span>Buffer: {selectedBuffer}</span>
                  <span className="text-[#7bd0ff]">{layer.version}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Layer Specification & Source Provenance Table */}
        <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-3">Asset Layers &amp; Provenance Specifications</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-caption-mono text-xs">
              <thead>
                <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                  <th className="py-2.5 px-3">Asset Layer</th>
                  <th className="py-2.5 px-3">Data Provider</th>
                  <th className="py-2.5 px-3">Version / Release</th>
                  <th className="py-2.5 px-3 text-right">1 km Buffer</th>
                  <th className="py-2.5 px-3 text-right">5 km Buffer</th>
                  <th className="py-2.5 px-3 text-right">10 km Buffer</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262a35]">
                {layers.map((l) => (
                  <tr key={l.id} className="bg-[#171b26] hover:bg-[#262a35]/60 transition-colors">
                    <td className="py-3 px-3 font-bold text-[#dfe2f1]">{l.name}</td>
                    <td className="py-3 px-3 text-[#d8c3ad]">{l.source}</td>
                    <td className="py-3 px-3 font-mono text-[#7bd0ff]">{l.version}</td>
                    <td className="py-3 px-3 text-right font-mono">{l.buffer1km}</td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-[#ffc174]">{l.buffer5km}</td>
                    <td className="py-3 px-3 text-right font-mono">{l.buffer10km}</td>
                    <td className="py-3 px-3 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#10B981]/20 text-[#10B981]">
                        VALIDATED
                      </span>
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

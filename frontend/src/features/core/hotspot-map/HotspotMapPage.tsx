import { useState } from 'react';
import FilterBar from '../../../components/filters/FilterBar';

export default function HotspotMapPage() {
  const [activeLayer, setActiveLayer] = useState<'hex' | 'raw' | 'frp'>('hex');
  const [h3Res, setH3Res] = useState<number>(7);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);
  const [selectedCell, setSelectedCell] = useState<{
    h3_cell: string;
    location: string;
    coords: string;
    totalDetections: number;
    viirsCount: number;
    modisCount: number;
    maxFrp: number;
    harmonizedValue: number;
    ci: [number, number];
  }>({
    h3_cell: '872830828ffffff',
    location: 'Willamette National Forest • Cedar Creek Corridor',
    coords: '44°07\'12"N, 121°51\'00"W',
    totalDetections: 842,
    viirsCount: 600,
    modisCount: 242,
    maxFrp: 412.0,
    harmonizedValue: 310.4,
    ci: [294.1, 328.0],
  });

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* Top Filter Strip */}
      <FilterBar />

      {/* Geospatial Map Canvas Frame */}
      <div className="relative flex-1 w-full bg-[#0a0e18] overflow-hidden flex flex-col">
        {/* Map Header HUD */}
        <div className="z-20 w-full px-6 py-2.5 bg-[#171b26]/95 backdrop-blur-md border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase mr-1">Layer:</span>
            <button
              onClick={() => setActiveLayer('hex')}
              className={`px-3 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                activeLayer === 'hex'
                  ? 'bg-[#f59e0b] text-[#0B0F19]'
                  : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
              }`}
            >
              <span className="material-symbols-outlined text-xs">grain</span>Harmonized Hexagons
            </button>
            <button
              onClick={() => setActiveLayer('raw')}
              className={`px-3 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                activeLayer === 'raw'
                  ? 'bg-[#f59e0b] text-[#0B0F19]'
                  : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
              }`}
            >
              <span className="material-symbols-outlined text-xs">scatter_plot</span>Raw Hotspot Points
            </button>
            <button
              onClick={() => setActiveLayer('frp')}
              className={`px-3 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                activeLayer === 'frp'
                  ? 'bg-[#f59e0b] text-[#0B0F19]'
                  : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
              }`}
            >
              <span className="material-symbols-outlined text-xs">local_fire_department</span>Thermal FRP Flux
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 bg-[#1c1f2a] px-2 py-0.5 rounded border border-[#262a35]">
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">H3 RES:</span>
              {[6, 7, 8].map((res) => (
                <button
                  key={res}
                  onClick={() => setH3Res(res)}
                  className={`px-1.5 py-0.5 font-caption-mono text-[10px] font-bold rounded transition-colors ${
                    h3Res === res
                      ? 'bg-[#00a6e0] text-[#00374d]'
                      : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
                  }`}
                >
                  {res}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  checked={showModis}
                  onChange={(e) => setShowModis(e.target.checked)}
                  className="w-3.5 h-3.5 rounded bg-[#1c1f2a] accent-[#c084fc]"
                  type="checkbox"
                />
                <span className="font-caption-mono text-[11px] text-[#c084fc]">MODIS 1km</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  checked={showViirs}
                  onChange={(e) => setShowViirs(e.target.checked)}
                  className="w-3.5 h-3.5 rounded bg-[#1c1f2a] accent-[#fb923c]"
                  type="checkbox"
                />
                <span className="font-caption-mono text-[11px] text-[#fb923c]">VIIRS 375m</span>
              </label>
            </div>
          </div>
        </div>

        {/* Viewport Canvas */}
        <div className="relative flex-1 w-full bg-[#0B0F19] overflow-hidden">
          {/* Subtle atmospheric starfield & graticule */}
          <div className="absolute inset-0 bg-[radial-gradient(#7bd0ff_1px,transparent_1px)] [background-size:36px_36px] opacity-15 pointer-events-none"></div>

          {/* SVG Cartographic Telemetry & Hexagons */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 1000 600">
            <defs>
              <radialGradient cx="50%" cy="50%" id="mapHexGlow" r="50%">
                <stop offset="0%" stopColor="#ff938c" stopOpacity="0.85"></stop>
                <stop offset="60%" stopColor="#f59e0b" stopOpacity="0.55"></stop>
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.05"></stop>
              </radialGradient>
            </defs>

            {/* Latitude / Longitude Graticule Lines */}
            <line opacity="0.2" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="250" x2="250" y1="0" y2="600"></line>
            <line opacity="0.2" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="500" x2="500" y1="0" y2="600"></line>
            <line opacity="0.2" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="750" x2="750" y1="0" y2="600"></line>
            <line opacity="0.2" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="0" x2="1000" y1="180" y2="180"></line>
            <line opacity="0.2" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="0" x2="1000" y1="360" y2="360"></line>

            {/* Interactive Hexagons */}
            <polygon
              fill="url(#mapHexGlow)"
              opacity="0.9"
              points="480,260 510,242 540,260 540,295 510,312 480,295"
              stroke="#ff938c"
              strokeWidth="1.5"
            ></polygon>
            <polygon
              fill="url(#mapHexGlow)"
              opacity="0.95"
              points="511,314 541,296 571,314 571,349 541,366 511,349"
              stroke="#ffbcb7"
              strokeWidth="2"
            ></polygon>
            {/* Active Hexagon Indicator */}
            <polygon
              className="animate-pulse"
              fill="none"
              points="511,314 541,296 571,314 571,349 541,366 511,349"
              stroke="#7bd0ff"
              strokeDasharray="6,4"
              strokeWidth="2.5"
            ></polygon>

            {/* Simulated VIIRS 375m points */}
            {showViirs && (
              <>
                <path d="M520,325 L525,334 L515,334 Z" fill="#fb923c"></path>
                <path d="M535,330 L540,339 L530,339 Z" fill="#fb923c"></path>
                <path d="M550,322 L555,331 L545,331 Z" fill="#fb923c"></path>
                <path d="M500,280 L505,289 L495,289 Z" fill="#fb923c"></path>
              </>
            )}

            {/* Simulated MODIS 1km points */}
            {showModis && (
              <>
                <circle cx="530" cy="330" fill="none" r="6" stroke="#c084fc" strokeWidth="2"></circle>
                <circle cx="505" cy="285" fill="none" r="6" stroke="#c084fc" strokeWidth="2"></circle>
              </>
            )}
          </svg>

          {/* Floating Reticle & Scale */}
          <div className="absolute top-4 left-4 bg-[#171b26]/90 backdrop-blur-md px-3.5 py-2 rounded border border-[#1F2937] flex items-center gap-3 pointer-events-auto">
            <div className="flex flex-col">
              <span className="font-caption-mono text-[9px] text-[#a08e7a]">DOMAIN CENTER</span>
              <span className="font-label-mono text-xs text-[#dfe2f1] font-semibold">{selectedCell.coords}</span>
            </div>
            <div className="w-px h-6 bg-[#313540]"></div>
            <div className="flex flex-col">
              <span className="font-caption-mono text-[9px] text-[#a08e7a]">APERTURE</span>
              <span className="font-label-mono text-xs text-[#7bd0ff]">H3 Resolution {h3Res} (~5.1 km²)</span>
            </div>
          </div>

          {/* Floating Cell Inspector */}
          <aside className="absolute top-4 right-4 w-76 rounded bg-[#1c1f2a]/95 backdrop-blur-md p-4 border border-[#262a35] shadow-2xl pointer-events-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="inline-flex items-center gap-1 font-caption-mono text-[10px] text-[#7bd0ff] font-bold">
                <span className="material-symbols-outlined text-xs">radar</span>CELL INSPECTOR
              </span>
              <span className="font-caption-mono text-[9px] px-1.5 py-0.5 rounded bg-[#00a6e0] text-[#00374d] font-bold">
                H3 Res {h3Res}
              </span>
            </div>
            <div className="font-mono text-sm font-bold text-[#ffc174] truncate">{selectedCell.h3_cell}</div>
            <div className="font-title-sm text-xs font-semibold text-[#dfe2f1] mt-0.5">{selectedCell.location}</div>

            <div className="mt-3 grid grid-cols-2 gap-2 bg-[#171b26] p-2.5 rounded border border-[#262a35] font-caption-mono text-xs">
              <div>
                <span className="text-[#a08e7a] text-[10px] block">TOTAL DETECTIONS</span>
                <span className="text-[#dfe2f1] font-bold">{selectedCell.totalDetections} spots</span>
              </div>
              <div>
                <span className="text-[#a08e7a] text-[10px] block">MAX FRP POWER</span>
                <span className="text-[#ffbcb7] font-bold">{selectedCell.maxFrp} MW</span>
              </div>
              <div>
                <span className="text-[#a08e7a] text-[10px] block">VIIRS (375M)</span>
                <span className="text-[#fb923c] font-bold">{selectedCell.viirsCount}</span>
              </div>
              <div>
                <span className="text-[#a08e7a] text-[10px] block">MODIS (1KM)</span>
                <span className="text-[#c084fc] font-bold">{selectedCell.modisCount}</span>
              </div>
            </div>

            <div className="mt-2.5 p-2 rounded bg-[#262a35] border border-[#313540] font-caption-mono text-xs">
              <div className="flex justify-between text-[#ffc174] font-bold">
                <span>HARMONIZED DAILY EQ:</span>
                <span>{selectedCell.harmonizedValue} / day</span>
              </div>
              <div className="flex justify-between text-[#a08e7a] text-[11px] mt-0.5">
                <span>95% Credible Interval:</span>
                <span className="text-[#dfe2f1]">[{selectedCell.ci[0]} – {selectedCell.ci[1]}]</span>
              </div>
            </div>

            <div className="mt-3 flex gap-2">
              <button
                onClick={() => setSelectedCell({ ...selectedCell, harmonizedValue: selectedCell.harmonizedValue + 1 })}
                className="flex-1 py-1.5 rounded bg-[#f59e0b] text-[#0B0F19] font-label-mono text-xs font-bold hover:bg-[#ffb95f] transition-colors"
              >
                Pin Hex Polygon
              </button>
            </div>
          </aside>

          {/* Bottom Left Legend */}
          <div className="absolute bottom-4 left-4 bg-[#171b26]/90 backdrop-blur-md px-3.5 py-2 rounded border border-[#1F2937] flex flex-col gap-1.5 pointer-events-auto">
            <div className="flex items-center justify-between gap-4 font-caption-mono text-[10px]">
              <span className="text-[#a08e7a] uppercase">Hex Radiance Flux Density</span>
              <span className="text-[#dfe2f1]">0 → &gt;120 MW/km²</span>
            </div>
            <div className="w-52 h-2 rounded-full bg-gradient-to-r from-[#313540] via-[#7bd0ff] to-[#ff938c]"></div>
            <div className="flex justify-between text-[9px] font-caption-mono text-[#a08e7a]">
              <span>Low (0.1)</span>
              <span>Nominal (45.0)</span>
              <span>Critical (&gt;100)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

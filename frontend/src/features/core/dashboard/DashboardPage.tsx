import { useState } from 'react';
import FilterBar from '../../../components/filters/FilterBar';

export default function DashboardPage() {
  const [activeOverlay, setActiveOverlay] = useState<'hex' | 'raw' | 'frp'>('hex');
  const [selectedHexRes, setSelectedHexRes] = useState<number>(7);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedCell] = useState<{
    id: string;
    location: string;
    coords: string;
    detections: number;
    maxFrp: number;
    viirsShare: string;
    modisCoDetect: number;
    harmonizedDaily: number;
    ci: [number, number];
  }>({
    id: '872830828ffffff',
    location: 'Willamette National Forest, OR',
    coords: '44.12°N, -121.85°W • Cedar Flats',
    detections: 842,
    maxFrp: 412.0,
    viirsShare: '71.2%',
    modisCoDetect: 242,
    harmonizedDaily: 310.4,
    ci: [294.1, 328.0],
  });

  return (
    <div className="flex flex-col w-full pb-12">
      {/* Synthetic Fixture Warning Banner */}
      <aside aria-label="Dataset status" className="w-full bg-[#0a0e18] px-6 py-1.5 flex flex-wrap items-center justify-between gap-2 border-b border-[#1F2937]">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-[10px] uppercase tracking-wider font-bold">
            SYNTHETIC FIXTURE [ACTIVE]
          </span>
          <span className="font-caption-mono text-xs text-[#dfe2f1] truncate">
            Ingest batch #ING-202611-042 • Overlap holdout validation active • DuckDB v1.1 WASM Partitioning
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-caption-mono text-[11px] text-[#a08e7a]">All figures illustrative for calibration benchmark</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#7bd0ff] animate-ping"></span>
            <span className="font-caption-mono text-[11px] text-[#7bd0ff] font-medium">PIPELINE VERIFIED</span>
          </div>
        </div>
      </aside>

      {/* Global Filter Telemetry Command Bar */}
      <FilterBar />

      {/* 4 Telemetry Metric Headline Cards */}
      <section aria-label="Key Observational Metrics" className="w-full px-6 py-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Metric 1: Harmonized Activity Index */}
          <div className="relative overflow-hidden rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col justify-between">
            <div className="absolute -right-4 -bottom-4 w-28 h-28 bg-[#ffc174]/5 rounded-full blur-xl pointer-events-none"></div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase tracking-wider">HARMONIZED FIRE ACTIVITY</span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-[#f59e0b]/20 text-[#ffc174] font-caption-mono text-[10px] font-medium">
                  M2 Stratified
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="font-mono-metric-lg text-2xl font-bold text-[#ffc174] tracking-tight">142,890</span>
                <span className="font-label-mono text-xs text-[#a08e7a]">±4,120</span>
              </div>
              <p className="font-caption-mono text-[10px] text-[#d8c3ad] mt-0.5">95% Bootstrap CI • Calibrated Index</p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#262a35] flex items-center justify-between">
              <span className="font-caption-mono text-xs text-[#7bd0ff] flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">trending_up</span>+14.2% vs 10-Yr Median
              </span>
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">Pacific NW Baseline</span>
            </div>
          </div>

          {/* Metric 2: MODIS Aqua / Terra Observed */}
          <div className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase tracking-wider">MODIS AQUA / TERRA</span>
                <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#ffbcb7] font-caption-mono text-[10px] uppercase font-bold">1.0 KM NADIR</span>
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="font-mono-metric-lg text-2xl font-bold text-[#dfe2f1] tracking-tight">48,320</span>
                <span className="font-caption-mono text-xs text-[#a08e7a]">points</span>
              </div>
              <p className="font-caption-mono text-[10px] text-[#d8c3ad] mt-0.5">4 daily overpasses • Saturated cores</p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#262a35] flex items-center justify-between">
              <span className="font-caption-mono text-xs text-[#ffb3ad]">MOD14 • MYD14 Products</span>
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">Res Ratio: 1.00x</span>
            </div>
          </div>

          {/* Metric 3: VIIRS SNPP / NOAA-20 Observed */}
          <div className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase tracking-wider">VIIRS SNPP / NOAA-20</span>
                <span className="px-1.5 py-0.5 rounded bg-[#313540] text-[#7bd0ff] font-caption-mono text-[10px] uppercase font-bold">375M I-BAND</span>
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="font-mono-metric-lg text-2xl font-bold text-[#7bd0ff] tracking-tight">118,450</span>
                <span className="font-caption-mono text-xs text-[#a08e7a]">points</span>
              </div>
              <p className="font-caption-mono text-[10px] text-[#d8c3ad] mt-0.5">VNP14IMG • Sub-pixel sensitivity</p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#262a35] flex items-center justify-between">
              <span className="font-caption-mono text-xs text-[#7bd0ff]">2.45x Hotspot Count Ratio</span>
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">Area: 0.14 km²</span>
            </div>
          </div>

          {/* Metric 4: Cross-Sensor Co-detection Agreement */}
          <div className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase tracking-wider">CO-DETECTION AGREEMENT</span>
                <span className="px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-[10px]">Window: ±45m</span>
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="font-mono-metric-lg text-2xl font-bold text-[#ffddb8] tracking-tight">78.4%</span>
                <span className="font-caption-mono text-xs text-[#a08e7a]">spatial overlap</span>
              </div>
              <p className="font-caption-mono text-[10px] text-[#d8c3ad] mt-0.5">Matched radius: 1.5 km • M2 active</p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#262a35] flex items-center justify-between">
              <span className="font-caption-mono text-xs text-[#ffc174]">Double-count removal: -32.8%</span>
              <span className="font-caption-mono text-[10px] text-[#a08e7a]">Stratified</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Command Viewport: 65% Geospatial Canvas / 35% Telemetry Inspector */}
      <div className="w-full px-6 flex-1 flex flex-col lg:flex-row gap-4">
        {/* LEFT PANEL (65%): Geospatial Hotspot & H3 Hex Map */}
        <section aria-label="Interactive NASA Geospatial Heatmap" className="lg:w-[65%] flex flex-col rounded bg-[#0a0e18] border border-[#1F2937] overflow-hidden shadow-xl relative min-h-[620px]">
          {/* Map Header HUD Controls */}
          <div className="z-20 w-full px-4 py-2.5 bg-[#171b26]/95 backdrop-blur-md border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3">
            {/* Layer Mode Buttons */}
            <div className="flex items-center gap-1.5">
              <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase mr-1">Overlay:</span>
              <button
                onClick={() => setActiveOverlay('hex')}
                className={`px-2.5 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1 transition-colors ${
                  activeOverlay === 'hex'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
                }`}
                type="button"
              >
                <span className="material-symbols-outlined text-xs">grain</span>Harmonized Hex
              </button>
              <button
                onClick={() => setActiveOverlay('raw')}
                className={`px-2.5 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1 transition-colors ${
                  activeOverlay === 'raw'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
                }`}
                type="button"
              >
                <span className="material-symbols-outlined text-xs">scatter_plot</span>Raw Hotspots
              </button>
              <button
                onClick={() => setActiveOverlay('frp')}
                className={`px-2.5 py-1 rounded font-label-mono text-xs font-semibold flex items-center gap-1 transition-colors ${
                  activeOverlay === 'frp'
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
                }`}
                type="button"
              >
                <span className="material-symbols-outlined text-xs">local_fire_department</span>FRP MW Flux
              </button>
            </div>

            {/* H3 Res & Sensor Toggle */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 bg-[#1c1f2a] px-2 py-0.5 rounded border border-[#262a35]">
                <span className="font-caption-mono text-[10px] text-[#a08e7a]">HEX RES:</span>
                {[6, 7, 8].map((res) => (
                  <button
                    key={res}
                    onClick={() => setSelectedHexRes(res)}
                    className={`px-1.5 py-0.5 font-caption-mono text-[10px] font-bold rounded transition-colors ${
                      selectedHexRes === res
                        ? 'bg-[#00a6e0] text-[#00374d]'
                        : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
                    }`}
                    type="button"
                  >
                    {res}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    checked={showModis}
                    onChange={(e) => setShowModis(e.target.checked)}
                    className="w-3.5 h-3.5 rounded bg-[#1c1f2a] accent-[#7bd0ff]"
                    type="checkbox"
                  />
                  <span className="font-caption-mono text-[10px] text-[#ffbcb7]">MODIS (48k)</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    checked={showViirs}
                    onChange={(e) => setShowViirs(e.target.checked)}
                    className="w-3.5 h-3.5 rounded bg-[#1c1f2a] accent-[#f59e0b]"
                    type="checkbox"
                  />
                  <span className="font-caption-mono text-[10px] text-[#ffc174]">VIIRS (118k)</span>
                </label>
              </div>
            </div>
          </div>

          {/* Primary Map Canvas Viewport */}
          <div className="relative flex-1 w-full min-h-[480px] bg-[#0a0e18] overflow-hidden">
            {/* Terrain Background Simulation */}
            <div className="absolute inset-0 bg-[#0B0F19] opacity-90"></div>
            <div className="absolute inset-0 bg-[radial-gradient(#7bd0ff_1px,transparent_1px)] [background-size:32px_32px] opacity-15 pointer-events-none"></div>

            {/* Simulated Cartographic SVG Overlays & H3 Hexagons */}
            <svg aria-hidden="true" className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 1000 600">
              <defs>
                <radialGradient cx="50%" cy="50%" id="dashHexGlowA" r="50%">
                  <stop offset="0%" stopColor="#ff938c" stopOpacity="0.85"></stop>
                  <stop offset="60%" stopColor="#f59e0b" stopOpacity="0.55"></stop>
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.05"></stop>
                </radialGradient>
                <radialGradient cx="50%" cy="50%" id="dashHexGlowB" r="50%">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.75"></stop>
                  <stop offset="100%" stopColor="#00a6e0" stopOpacity="0.15"></stop>
                </radialGradient>
              </defs>

              {/* Grid Lines */}
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="200" x2="200" y1="40" y2="560"></line>
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="500" x2="500" y1="40" y2="560"></line>
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="800" x2="800" y1="40" y2="560"></line>
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="40" x2="960" y1="150" y2="150"></line>
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="40" x2="960" y1="320" y2="320"></line>
              <line opacity="0.25" stroke="#7bd0ff" strokeDasharray="3,6" strokeWidth="0.75" x1="40" x2="960" y1="470" y2="470"></line>

              {/* Hexagon Cluster Polygons */}
              <polygon fill="url(#dashHexGlowA)" opacity="0.9" points="460,250 490,232 520,250 520,285 490,302 460,285" stroke="#ff938c" strokeWidth="1.5"></polygon>
              <polygon fill="url(#dashHexGlowA)" opacity="0.85" points="522,250 552,232 582,250 582,285 552,302 522,285" stroke="#f59e0b" strokeWidth="1.2"></polygon>
              <polygon fill="url(#dashHexGlowA)" opacity="0.95" points="491,304 521,286 551,304 551,339 521,356 491,339" stroke="#ffbcb7" strokeWidth="2"></polygon>
              <polygon className="animate-pulse" fill="none" points="491,304 521,286 551,304 551,339 521,356 491,339" stroke="#7bd0ff" strokeDasharray="6,4" strokeWidth="2.5"></polygon>
              <polygon fill="url(#dashHexGlowB)" opacity="0.65" points="429,232 459,214 489,232 489,267 459,284 429,267" stroke="#f59e0b" strokeWidth="1"></polygon>
              <polygon fill="url(#dashHexGlowB)" opacity="0.55" points="553,232 583,214 613,232 613,267 583,284 553,267" stroke="#f59e0b" strokeWidth="1"></polygon>

              {/* VIIRS Hotspots */}
              {showViirs && (
                <>
                  <path d="M500,315 L505,324 L495,324 Z" fill="#ffc174"></path>
                  <path d="M512,328 L517,337 L507,337 Z" fill="#ffc174"></path>
                  <path d="M528,312 L533,321 L523,321 Z" fill="#ff938c"></path>
                  <path d="M535,325 L540,334 L530,334 Z" fill="#ffc174"></path>
                  <path d="M480,265 L485,274 L475,274 Z" fill="#ffc174"></path>
                </>
              )}

              {/* MODIS Hotspots */}
              {showModis && (
                <>
                  <circle cx="508" cy="320" fill="none" r="5.5" stroke="#ffbcb7" strokeWidth="2"></circle>
                  <circle cx="530" cy="322" fill="none" r="5.5" stroke="#ffbcb7" strokeWidth="2"></circle>
                  <circle cx="482" cy="270" fill="none" r="5.5" stroke="#ffbcb7" strokeWidth="2"></circle>
                </>
              )}
            </svg>

            {/* Floating HUD: Coordinates */}
            <div className="absolute top-4 left-4 bg-[#171b26]/90 backdrop-blur-md px-3 py-1.5 rounded border border-[#1F2937] flex items-center gap-3 pointer-events-auto">
              <div className="flex flex-col">
                <span className="font-caption-mono text-[9px] text-[#a08e7a]">CENTER FOCUS</span>
                <span className="font-label-mono text-xs text-[#dfe2f1] font-semibold">44°07'12"N, 121°51'00"W</span>
              </div>
              <div className="w-px h-6 bg-[#313540]"></div>
              <div className="flex flex-col">
                <span className="font-caption-mono text-[9px] text-[#a08e7a]">NADIR SCALE</span>
                <span className="font-label-mono text-xs text-[#7bd0ff]">1:250,000 (1cm = 2.5km)</span>
              </div>
            </div>

            {/* Floating Inspector Card for Selected H3 Cell */}
            <aside aria-label="Inspected H3 Geospatial Tile" className="absolute top-4 right-4 w-72 rounded bg-[#1c1f2a]/95 backdrop-blur-md p-3.5 border border-[#262a35] shadow-xl pointer-events-auto">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 font-caption-mono text-[10px] text-[#7bd0ff] font-semibold">
                  <span className="material-symbols-outlined text-xs">radar</span>CELL INSPECTOR
                </span>
                <span className="font-caption-mono text-[9px] px-1.5 py-0.5 rounded bg-[#00a6e0] text-[#00374d] font-bold">
                  H3 Res {selectedHexRes}
                </span>
              </div>
              <div className="mt-1.5">
                <div className="font-mono-metric-md text-sm font-bold text-[#ffc174] truncate">{selectedCell.id}</div>
                <p className="font-body-sm text-xs text-[#dfe2f1] font-medium">{selectedCell.location}</p>
                <span className="font-caption-mono text-[9px] text-[#a08e7a]">{selectedCell.coords}</span>
              </div>

              {/* Cell Stat Matrix */}
              <div className="mt-2.5 grid grid-cols-2 gap-1.5 bg-[#171b26] p-2 rounded border border-[#1F2937]">
                <div>
                  <span className="font-caption-mono text-[9px] text-[#a08e7a] block">TOTAL DETECTIONS</span>
                  <span className="font-label-mono text-xs text-[#dfe2f1] font-bold">{selectedCell.detections} spots</span>
                </div>
                <div>
                  <span className="font-caption-mono text-[9px] text-[#a08e7a] block">MAX FRP POWER</span>
                  <span className="font-label-mono text-xs text-[#ffbcb7] font-bold">{selectedCell.maxFrp} MW</span>
                </div>
                <div>
                  <span className="font-caption-mono text-[9px] text-[#a08e7a] block">DOMINANT SENSOR</span>
                  <span className="font-label-mono text-xs text-[#ffc174] font-bold">VIIRS ({selectedCell.viirsShare})</span>
                </div>
                <div>
                  <span className="font-caption-mono text-[9px] text-[#a08e7a] block">MODIS CO-DETECT</span>
                  <span className="font-label-mono text-xs text-[#dfe2f1]">{selectedCell.modisCoDetect} spots</span>
                </div>
              </div>

              {/* Harmonized Daily Activity Calculation */}
              <div className="mt-2 p-2 rounded bg-[#262a35] border border-[#313540]">
                <div className="flex items-center justify-between text-[10px] font-caption-mono">
                  <span className="text-[#a08e7a] uppercase">HARMONIZED DAILY EQ:</span>
                  <span className="text-[#ffc174] font-bold">{selectedCell.harmonizedDaily} / day</span>
                </div>
                <div className="flex items-center justify-between text-[10px] font-caption-mono mt-0.5">
                  <span className="text-[#a08e7a]">95% Credible Interval:</span>
                  <span className="text-[#dfe2f1] font-mono">[{selectedCell.ci[0]} – {selectedCell.ci[1]}]</span>
                </div>
              </div>

              {/* Inspector Action Buttons */}
              <div className="mt-3 flex items-center gap-2">
                <button className="flex-1 py-1 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-xs font-bold hover:bg-[#ffb95f] transition-colors" type="button">
                  Pin Hex Cell
                </button>
                <button className="px-2.5 py-1 rounded bg-[#262a35] text-[#dfe2f1] hover:text-[#7bd0ff] font-caption-mono text-xs transition-colors" title="Export Polygon WKT" type="button">
                  WKT
                </button>
              </div>
            </aside>

            {/* Color Ramp Legend HUD */}
            <div className="absolute bottom-4 left-4 bg-[#171b26]/90 backdrop-blur-md px-3 py-2 rounded border border-[#1F2937] flex flex-col gap-1 pointer-events-auto">
              <div className="flex items-center justify-between gap-4">
                <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">Density Index (Hotspots/km²)</span>
                <span className="font-caption-mono text-[10px] text-[#dfe2f1]">0 → &gt;120 MW/km²</span>
              </div>
              <div className="w-48 h-2 rounded-full bg-gradient-to-r from-[#313540] via-[#7bd0ff] to-[#ff938c]"></div>
              <div className="flex justify-between text-[9px] font-caption-mono text-[#a08e7a]">
                <span>Low (0.1)</span>
                <span>Nominal (45.0)</span>
                <span>Critical (&gt;100)</span>
              </div>
            </div>
          </div>

          {/* Time Scrubber Playback Bar */}
          <footer aria-label="Geospatial Time-Series Scrubber" className="w-full px-4 py-2 bg-[#171b26] border-t border-[#1F2937] flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="w-7 h-7 rounded bg-[#f59e0b] text-[#0B0F19] flex items-center justify-center hover:bg-[#ffb95f] transition-colors"
                  type="button"
                >
                  <span className="material-symbols-outlined text-base">{isPlaying ? 'pause' : 'play_arrow'}</span>
                </button>
                <span className="font-label-mono text-xs text-[#dfe2f1] font-semibold ml-2">2024-08-18 (Peak Fire Season)</span>
                <span className="font-caption-mono text-[10px] text-[#a08e7a]">DOY 231 • Cedar Creek Event</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-caption-mono text-[10px] text-[#a08e7a]">Playback Speed:</span>
                <span className="px-1.5 py-0.5 rounded bg-[#1c1f2a] font-caption-mono text-[10px] text-[#dfe2f1] font-semibold">1x Daily</span>
              </div>
            </div>

            {/* Slider Bar */}
            <div className="relative w-full flex items-center py-1">
              <div className="w-full h-1.5 rounded-full bg-[#313540] relative">
                <div className="absolute left-[60%] w-[25%] h-full bg-[#ffc174]/20 rounded"></div>
                <div className="absolute left-0 w-[68%] h-full bg-[#f59e0b] rounded"></div>
                <div className="absolute left-[68%] -top-1.5 w-4 h-4 bg-[#ffc174] text-[#0B0F19] rounded shadow flex items-center justify-center cursor-pointer">
                  <div className="w-1.5 h-1.5 bg-[#0B0F19] rounded-full"></div>
                </div>
              </div>
            </div>
            <div className="flex justify-between font-caption-mono text-[9px] text-[#a08e7a]">
              <span>2024-06-01 (Early Season)</span>
              <span className="text-[#ffc174] font-semibold">Peak Surge (Aug 15 - Sep 02)</span>
              <span>2024-10-31 (Post-Season Rain)</span>
            </div>
          </footer>
        </section>

        {/* RIGHT PANEL (35%): Telemetry & Harmonization Insights */}
        <aside aria-label="Harmonization Intelligence Analytics" className="lg:w-[35%] flex flex-col gap-4">
          {/* Card 1: Temporal Sensor Convergence */}
          <section aria-label="Temporal Fire Trajectory" className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-title-sm text-sm text-[#dfe2f1] font-bold">Temporal Sensor Convergence</h2>
                <span className="font-caption-mono text-[9px] text-[#a08e7a]">Weekly Rolling Mean Hotspot Activity • 2024</span>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-[10px]">95% CI Range</span>
            </div>

            {/* Multi-Line SVG Chart */}
            <div className="w-full h-44 bg-[#0a0e18] rounded p-2 relative overflow-hidden flex flex-col justify-end border border-[#1F2937]">
              <svg aria-label="Sensor trend comparison chart" className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 400 140">
                <line stroke="#313540" strokeDasharray="2,4" strokeWidth="0.75" x1="0" x2="400" y1="35" y2="35"></line>
                <line stroke="#313540" strokeDasharray="2,4" strokeWidth="0.75" x1="0" x2="400" y1="70" y2="70"></line>
                <line stroke="#313540" strokeDasharray="2,4" strokeWidth="0.75" x1="0" x2="400" y1="105" y2="105"></line>
                <path d="M 0,130 Q 80,128 140,115 T 230,55 T 290,15 T 350,75 T 400,120 L 400,135 L 350,95 L 290,35 L 230,75 L 140,128 L 0,135 Z" fill="#f59e0b" fillOpacity="0.18"></path>
                <path d="M 0,132 Q 80,130 140,120 T 230,85 T 290,52 T 350,98 T 400,128" fill="none" stroke="#ffbcb7" strokeDasharray="4,2" strokeWidth="1.8"></path>
                <path d="M 0,125 Q 80,120 140,105 T 230,42 T 290,18 T 350,68 T 400,115" fill="none" stroke="#7bd0ff" strokeWidth="1.8"></path>
                <path d="M 0,128 Q 80,124 140,112 T 230,58 T 290,26 T 350,82 T 400,122" fill="none" stroke="#ffc174" strokeWidth="2.5"></path>
                <circle cx="290" cy="26" fill="#ffc174" r="4" stroke="#0a0e18" strokeWidth="1.5"></circle>
              </svg>
              <div className="flex items-center justify-between text-[9px] font-caption-mono pt-1 text-[#d8c3ad]">
                <div className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-[#ffc174] inline-block"></span>
                  <span className="text-[#dfe2f1] font-semibold">Harmonized</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-[#7bd0ff] inline-block"></span>
                  <span>VIIRS 375m</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-[#ffbcb7] inline-block border-dashed"></span>
                  <span>MODIS 1km</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-2 bg-[#f59e0b]/20 inline-block"></span>
                  <span>±95% CI</span>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between font-caption-mono text-[9px] text-[#a08e7a]">
              <span>MAY</span>
              <span>JUN</span>
              <span>JUL</span>
              <span className="text-[#ffc174] font-bold">AUG (PEAK)</span>
              <span>SEP</span>
              <span>OCT</span>
            </div>
          </section>

          {/* Card 2: Instrument Divergence Diagnostic */}
          <section aria-label="Methodological Rationale" className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#ffc174] text-base">warning</span>
              <h2 className="font-title-sm text-sm text-[#ffc174] font-bold">Divergence Alert: Why Naive Sum Fails</h2>
            </div>
            <div className="p-2.5 rounded bg-[#0a0e18] border border-[#1F2937] flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] font-caption-mono">
                <span className="text-[#ffbcb7]">Raw Sum (MODIS + VIIRS):</span>
                <span className="text-[#ffbcb7] font-bold line-through">166,770 spots</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-caption-mono">
                <span className="text-[#ffc174] font-semibold">Harmonized Deduplicated Index:</span>
                <span className="text-[#ffc174] font-mono font-bold">142,890 ± 4k</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-caption-mono text-[#a08e7a]">
                <span>Pixel Inflation Overcount:</span>
                <span className="text-[#7bd0ff] font-bold">+23,880 false counts (+16.7%)</span>
              </div>
            </div>

            {/* Footprint Disparity Diagram */}
            <div className="p-2.5 rounded bg-[#171b26] border border-[#1F2937] flex items-center gap-3">
              <div className="w-14 h-14 rounded bg-[#0a0e18] p-1 flex items-center justify-center relative shrink-0">
                <div className="w-12 h-12 border border-[#ffbcb7]/40 bg-[#ffbcb7]/10 rounded flex items-center justify-center">
                  <div className="grid grid-cols-2 gap-0.5">
                    <span className="w-2 h-2 rounded-sm bg-[#ffc174]/80"></span>
                    <span className="w-2 h-2 rounded-sm bg-[#ffc174]/80"></span>
                    <span className="w-2 h-2 rounded-sm bg-[#ffc174]/40"></span>
                    <span className="w-2 h-2 rounded-sm bg-transparent"></span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col">
                <span className="font-label-mono text-xs text-[#dfe2f1] font-semibold">Footprint Disparity (~7.1x)</span>
                <p className="font-body-sm text-[11px] text-[#d8c3ad] leading-tight mt-0.5">
                  One MODIS 1km pixel contains ~7 VIIRS 375m pixels. Counting both registers the same flame up to 8 times without cross-sensor calibration.
                </p>
              </div>
            </div>
          </section>

          {/* Card 3: Analytical Export & Provenance */}
          <section aria-label="Data Pipeline Actions" className="rounded bg-[#1c1f2a] p-4 border border-[#262a35] shadow-md flex flex-col gap-2.5">
            <h2 className="font-title-sm text-sm text-[#dfe2f1] font-bold">Analytical Export &amp; Provenance</h2>
            <div className="grid grid-cols-2 gap-2">
              <button className="px-3 py-2 rounded bg-[#f59e0b] text-[#0B0F19] hover:bg-[#ffb95f] transition-colors font-label-mono text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm" type="button">
                <span className="material-symbols-outlined text-sm">cloud_download</span>
                Export CSV
              </button>
              <button className="px-3 py-2 rounded bg-[#262a35] text-[#dfe2f1] hover:bg-[#313540] transition-colors font-label-mono text-xs flex items-center justify-center gap-1.5" type="button">
                <span className="material-symbols-outlined text-sm">history_edu</span>
                Lineage
              </button>
            </div>
            <div className="flex items-center justify-between font-caption-mono text-[9px] text-[#a08e7a] pt-1 border-t border-[#262a35]">
              <span>DuckDB Thread Pool: 8 cores</span>
              <span>Latency: 18.4ms</span>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

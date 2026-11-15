import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';

import { getRegions, getHotspots, getHotspotCells } from '../../../api/core';

maplibregl.setWorkerUrl(workerUrl);

type HotspotsData = Awaited<ReturnType<typeof getHotspots>>['data'];
type CellsData = Awaited<ReturnType<typeof getHotspotCells>>['data'];
type RegionsData = Awaited<ReturnType<typeof getRegions>>['data'];

type ActiveLayer = 'hex' | 'raw' | 'frp';

// Optional fields the FIRMS backend adds; typed locally so older types still compile.
type CellExtra = {
  frp_sum_modis?: number | null;
  frp_sum_viirs?: number | null;
};
type CellsMeta = {
  total_cells?: number;
  truncated?: boolean;
  window?: { start?: string | null; end?: string | null; basis?: string };
};
type HotspotsMeta = { total_matching?: number; truncated?: boolean };

// OSM tiles (no API key), desaturated and dimmed to look dark.
const MAP_STYLE = {
  version: 8,
  sources: {
    basemap: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#0B0F19' } },
    {
      id: 'basemap',
      type: 'raster',
      source: 'basemap',
      paint: {
        'raster-saturation': -0.85,
        'raster-brightness-max': 0.38,
        'raster-contrast': 0.15,
      },
    },
  ],
} as maplibregl.StyleSpecification;

const SRC = 'terraflare-hotspots';
const LYR = 'terraflare-hotspot-points';

const formatNumber = (value: number | null | undefined) =>
  value == null
    ? '—'
    : value.toLocaleString('en-IN', { maximumFractionDigits: 2 });

const EMPTY_FC = { type: 'FeatureCollection', features: [] } as unknown as HotspotsData;

export default function HotspotMapPage() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [mapReady, setMapReady] = useState(false);
  const [activeLayer, setActiveLayer] = useState<ActiveLayer>('hex');
  const [h3Res, setH3Res] = useState(5);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);

  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCellId, setSelectedCellId] = useState('');

  const [regions, setRegions] = useState<RegionsData['regions']>([]);
  const [hotspots, setHotspots] = useState<HotspotsData | null>(null);
  const [cells, setCells] = useState<CellsData | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const selectedCell = useMemo(
    () => cells?.cells.find((cell) => cell.h3_cell === selectedCellId) ?? null,
    [cells, selectedCellId]
  );

  const region = regions.find((item) => item.region_id === selectedRegion);

  const selectedSensors = useMemo(() => {
    const sensors: string[] = [];
    if (showModis) sensors.push('MODIS');
    if (showViirs) sensors.push('VIIRS');
    return sensors;
  }, [showModis, showViirs]);

  const cellsMeta = cells as unknown as CellsMeta | null;
  const hotspotsMeta = hotspots as unknown as HotspotsMeta | null;
  const selectedExtra = selectedCell as unknown as CellExtra | null;

  // Load regions first so a valid region is always selected.
  useEffect(() => {
    let cancelled = false;

    getRegions()
      .then((response) => {
        if (cancelled) return;
        const list = response.data.regions;
        setRegions(list);
        setSelectedRegion((current) =>
          list.some((item) => item.region_id === current)
            ? current
            : list[0]?.region_id ?? ''
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load regions.');
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Load geospatial data.
  useEffect(() => {
    if (!selectedRegion) return;

    let cancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError('');

      try {
        const cellPromise = getHotspotCells({
          region_id: selectedRegion,
          h3_res: h3Res,
        });
        const hotspotPromise =
          selectedSensors.length === 0
            ? Promise.resolve(null)
            : getHotspots({
                region_id: selectedRegion,
                sensors: selectedSensors.join(','),
                limit: 10000,
              });

        const [hotspotResponse, cellResponse] = await Promise.all([
          hotspotPromise,
          cellPromise,
        ]);

        if (cancelled) return;

        setHotspots(hotspotResponse ? hotspotResponse.data : EMPTY_FC);
        setCells(cellResponse.data);

        setSelectedCellId((current) =>
          cellResponse.data.cells.some((cell) => cell.h3_cell === current)
            ? current
            : cellResponse.data.cells[0]?.h3_cell ?? ''
        );
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load hotspot data:', err);
        setError(
          err instanceof Error ? err.message : 'Unable to load geospatial data.'
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [selectedRegion, h3Res, selectedSensors, reloadKey]);

  // Initialize MapLibre.
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLE,
      center: [0, 20],
      zoom: 1.5,
      minZoom: 1,
      renderWorldCopies: false,
      attributionControl: { compact: true },
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('load', () => {
      map.resize();
      setMapReady(true);
    });
    map.on('error', (e) => console.error('MapLibre error:', e.error));

    mapRef.current = map;

    return () => {
      setMapReady(false);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update map position when region changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !region?.bbox) return;

    const [west, south, east, north] = region.bbox;

    map.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 70, duration: 1000, maxZoom: 8 }
    );
  }, [region, mapReady]);

  // Add hotspot GeoJSON and update styling.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !hotspots || !mapReady) return;

    const data = hotspots as unknown as GeoJSON.FeatureCollection;

    const existingSource = map.getSource(SRC) as
      | maplibregl.GeoJSONSource
      | undefined;

    if (existingSource) {
      existingSource.setData(data);
    } else {
      map.addSource(SRC, { type: 'geojson', data });
    }

    if (!map.getLayer(LYR)) {
      map.addLayer({
        id: LYR,
        type: 'circle',
        source: SRC,
        paint: {
          'circle-radius': 3,
          'circle-color': '#fb923c',
          'circle-opacity': 0.8,
          'circle-stroke-width': 0,
        },
      });

      map.on('click', LYR, (event: maplibregl.MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== 'Point') return;

        const coordinates = feature.geometry.coordinates as [number, number];
        const p = feature.properties ?? {};

        const content = document.createElement('div');
        content.style.color = '#111827';
        content.style.fontFamily = 'monospace';
        content.style.fontSize = '12px';

        const heading = document.createElement('strong');
        heading.textContent = 'Satellite Observation';
        content.appendChild(heading);

        const fields: [string, unknown][] = [
          ['Sensor', p.sensor_family ?? 'Unknown'],
          ['Platform', p.platform ?? '—'],
          ['Processing', p.processing_stream ?? p.product_type ?? 'not available'],
          ['Time (UTC)', p.acq_datetime_utc ?? '—'],
          ['Confidence', `${p.confidence_raw ?? '—'} (${p.confidence_class ?? '—'})`],
          ['FRP', `${p.frp_mw ?? '—'} MW`],
          ['Source', p.source_dataset ?? '—'],
        ];

        fields.forEach(([label, value]) => {
          const line = document.createElement('div');
          line.textContent = `${label}: ${String(value)}`;
          content.appendChild(line);
        });

        new maplibregl.Popup()
          .setLngLat(coordinates)
          .setDOMContent(content)
          .addTo(map);
      });

      map.on('mouseenter', LYR, () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', LYR, () => {
        map.getCanvas().style.cursor = '';
      });
    }

    if (activeLayer === 'frp') {
      map.setPaintProperty(LYR, 'circle-radius', [
        'interpolate', ['linear'], ['coalesce', ['get', 'frp_mw'], 0],
        0, 2, 50, 4, 200, 8, 500, 12,
      ]);
      map.setPaintProperty(LYR, 'circle-color', [
        'interpolate', ['linear'], ['coalesce', ['get', 'frp_mw'], 0],
        0, '#7bd0ff', 50, '#f59e0b', 200, '#ff938c', 500, '#ef4444',
      ]);
    } else {
      map.setPaintProperty(LYR, 'circle-radius', 3);
      map.setPaintProperty(LYR, 'circle-color', [
        'match',
        ['upcase', ['to-string', ['get', 'sensor_family']]],
        'MODIS', '#c084fc',
        'VIIRS', '#fb923c',
        '#7bd0ff',
      ]);
    }
  }, [hotspots, activeLayer, mapReady]);

  const handleCellSelect = useCallback((cellId: string) => {
    setSelectedCellId(cellId);
  }, []);

  const features = hotspots?.features ?? [];
  const hotspotCount = features.length;
  const totalMatching = hotspotsMeta?.total_matching ?? hotspotCount;

  const sensorOf = (f: (typeof features)[number]) =>
    String(f.properties?.sensor_family ?? '').toUpperCase();
  const modisCount = features.filter((f) => sensorOf(f) === 'MODIS').length;
  const viirsCount = features.filter((f) => sensorOf(f) === 'VIIRS').length;

  return (
    <div className="flex flex-col h-full min-h-[700px] w-full overflow-hidden">
      {/* Header */}
      <div className="z-20 w-full px-6 py-3 bg-[#171b26] border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-caption-mono text-[10px] text-[#a08e7a] uppercase">
            REGION
          </span>

          <select
            value={selectedRegion}
            onChange={(event) => setSelectedRegion(event.target.value)}
            className="bg-[#0a0e18] border border-[#262a35] rounded px-3 py-1.5 text-xs text-[#dfe2f1]"
          >
            {regions.map((item) => (
              <option key={item.region_id} value={item.region_id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-caption-mono text-[10px] text-[#a08e7a]">
            LAYER
          </span>

          {([
            ['hex', 'H3 Cells'],
            ['raw', 'Raw Hotspots'],
            ['frp', 'FRP Intensity'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setActiveLayer(value)}
              className={`px-3 py-1.5 rounded font-label-mono text-xs font-semibold transition-colors ${
                activeLayer === value
                  ? 'bg-[#f59e0b] text-[#0B0F19]'
                  : 'bg-[#1c1f2a] text-[#dfe2f1] hover:bg-[#262a35]'
              }`}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="z-20 w-full px-6 py-3 bg-[#0a0e18] border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#171b26] px-2 py-1 rounded border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a]">
              H3 RES:
            </span>

            {[4, 5, 6, 7].map((res) => (
              <button
                key={res}
                onClick={() => setH3Res(res)}
                className={`px-2 py-1 font-caption-mono text-[10px] font-bold rounded ${
                  h3Res === res
                    ? 'bg-[#00a6e0] text-[#00374d]'
                    : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
                }`}
                type="button"
              >
                {res}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              checked={showModis}
              onChange={(event) => setShowModis(event.target.checked)}
              className="accent-[#c084fc]"
              type="checkbox"
            />
            <span className="font-caption-mono text-[11px] text-[#c084fc]">
              MODIS
            </span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              checked={showViirs}
              onChange={(event) => setShowViirs(event.target.checked)}
              className="accent-[#fb923c]"
              type="checkbox"
            />
            <span className="font-caption-mono text-[11px] text-[#fb923c]">
              VIIRS
            </span>
          </label>
        </div>

        <div className="flex items-center gap-4 font-caption-mono text-[10px] text-[#a08e7a]">
          <span>
            SHOWN: {formatNumber(hotspotCount)} / MATCHING: {formatNumber(totalMatching)}
          </span>
          <span className="text-[#c084fc]">MODIS: {formatNumber(modisCount)}</span>
          <span className="text-[#fb923c]">VIIRS: {formatNumber(viirsCount)}</span>
        </div>
      </div>

      {/* Main map and inspector */}
      <div className="relative flex-1 min-h-[520px] bg-[#0B0F19]">
        <div
          ref={mapContainerRef}
          style={{ position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 }}
        />

        {/* Map status */}
        <div className="absolute top-4 left-4 z-10 bg-[#171b26]/95 px-3 py-2 rounded border border-[#262a35]">
          <div className="font-caption-mono text-[9px] text-[#a08e7a]">
            SELECTED REGION
          </div>

          <div className="font-label-mono text-xs text-[#dfe2f1]">
            {region?.name ?? selectedRegion}
          </div>

          <div className="font-caption-mono text-[9px] text-[#7bd0ff] mt-1">
            {activeLayer === 'frp'
              ? 'POINT SIZE AND COLOR REPRESENT FRP'
              : activeLayer === 'raw'
                ? 'SATELLITE HOTSPOT OBSERVATIONS'
                : `H3 RESOLUTION ${h3Res} — CELL DATA PANEL`}
          </div>
        </div>

        {/* Inspector */}
        <aside className="absolute top-4 right-4 z-10 w-[310px] max-w-[calc(100%-2rem)] max-h-[calc(100%-2rem)] overflow-y-auto rounded bg-[#1c1f2a]/95 backdrop-blur-md p-4 border border-[#262a35] shadow-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="font-caption-mono text-[10px] text-[#7bd0ff] font-bold">
              {activeLayer === 'hex' ? 'H3 CELL INSPECTOR' : 'MAP DATA INSPECTOR'}
            </span>

            <span className="font-caption-mono text-[9px] px-2 py-1 rounded bg-[#00a6e0] text-[#00374d] font-bold">
              RES {h3Res}
            </span>
          </div>

          {isLoading && (
            <p className="text-xs text-[#a08e7a] py-6">
              Loading satellite observations...
            </p>
          )}

          {!isLoading && error && (
            <div>
              <p className="text-xs text-red-400 mb-3">{error}</p>

              <button
                type="button"
                onClick={() => setReloadKey((value) => value + 1)}
                className="px-3 py-1.5 rounded bg-[#f59e0b] text-[#0B0F19] text-xs font-bold"
              >
                Retry
              </button>
            </div>
          )}

          {!isLoading && !error && selectedCell && (
            <>
              <div className="font-mono text-sm font-bold text-[#ffc174] break-all">
                {selectedCell.h3_cell}
              </div>

              <div className="mt-3 p-3 rounded border border-[#262a35] bg-[#171b26] font-caption-mono text-[10px] text-[#a08e7a]">
                Harmonized value: not available at cell level. In the VIIRS era the
                harmonized series equals the NOAA-20 observation, so no MODIS
                conversion is applied and cell-level MODIS-equivalent values are not produced.
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-caption-mono">
                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#c084fc] text-[10px]">
                    MODIS DETECTIONS
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.modis_observed)}
                  </span>
                </div>

                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#fb923c] text-[10px]">
                    VIIRS DETECTIONS
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.viirs_observed)}
                  </span>
                </div>

                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#c084fc] text-[10px]">
                    MODIS FRP SUM (MW)
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedExtra?.frp_sum_modis)}
                  </span>
                </div>

                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#fb923c] text-[10px]">
                    VIIRS FRP SUM (MW)
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedExtra?.frp_sum_viirs)}
                  </span>
                </div>
              </div>

              {cellsMeta?.window && (
                <div className="mt-3 font-caption-mono text-[10px] text-[#a08e7a] break-words">
                  WINDOW ({cellsMeta.window.basis ?? '—'}):
                  <br />
                  {cellsMeta.window.start ?? '—'}
                  <br />→ {cellsMeta.window.end ?? '—'}
                </div>
              )}
            </>
          )}

          {!isLoading && !error && !selectedCell && (
            <p className="text-xs text-[#a08e7a] py-6">
              No H3 cell records are available for this region and resolution.
            </p>
          )}

          <div className="mt-4 pt-3 border-t border-[#262a35]">
            <div className="font-caption-mono text-[10px] text-[#7bd0ff] mb-2">
              TOP H3 CELLS ({cells?.cells.length ?? 0}
              {cellsMeta?.total_cells != null
                ? ` of ${formatNumber(cellsMeta.total_cells)}`
                : ''}
              )
            </div>

            <div className="max-h-48 overflow-y-auto space-y-1">
              {cells?.cells.map((cell) => (
                <button
                  key={cell.h3_cell}
                  type="button"
                  onClick={() => handleCellSelect(cell.h3_cell)}
                  className={`w-full text-left px-2 py-2 rounded font-mono text-[10px] transition-colors ${
                    selectedCellId === cell.h3_cell
                      ? 'bg-[#f59e0b]/20 border border-[#f59e0b]/50 text-[#ffc174]'
                      : 'bg-[#171b26] text-[#a08e7a] hover:text-[#dfe2f1]'
                  }`}
                >
                  <div className="flex justify-between gap-2">
                    <span className="truncate">{cell.h3_cell}</span>
                    <span>
                      M {formatNumber(cell.modis_observed)} · V{' '}
                      {formatNumber(cell.viirs_observed)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-10 bg-[#171b26]/95 px-3.5 py-2 rounded border border-[#262a35]">
          <div className="font-caption-mono text-[10px] text-[#a08e7a] mb-2">
            SATELLITE OBSERVATION LEGEND
          </div>

          <div className="flex flex-col gap-1.5 text-[10px] font-caption-mono">
            <span className="flex items-center gap-2 text-[#c084fc]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#c084fc]" />
              MODIS
            </span>

            <span className="flex items-center gap-2 text-[#fb923c]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#fb923c]" />
              VIIRS
            </span>

            {activeLayer === 'frp' && (
              <span className="text-[#ffc174] mt-1">
                Larger/brighter points indicate higher FRP.
              </span>
            )}
          </div>
        </div>

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center">
            <div className="bg-[#171b26]/95 border border-[#262a35] rounded-lg px-5 py-3 flex items-center gap-3">
              <span className="material-symbols-outlined animate-spin text-[#f59e0b]">
                progress_activity
              </span>

              <span className="font-caption-mono text-xs text-[#dfe2f1]">
                FETCHING SATELLITE DATA
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Scientific limitation note */}
      <div className="px-5 py-2 bg-[#171b26] border-t border-[#262a35]">
        <p className="font-caption-mono text-[10px] text-[#a08e7a]">
          Data combine standard-processing (SP) history and provisional NRT
          (near real-time) detections; NRT is not science-quality. Hotspots are
          satellite-observed thermal anomalies, not confirmed unique fires, and
          are not merged across sensors. MODIS (1 km) and VIIRS (375 m) counts
          differ in resolution and sensitivity. Map points are truncated to an
          equal share per sensor, highest FRP first. Polygon geometry is not
          supplied by the cell API.
        </p>
      </div>
    </div>
  );
}
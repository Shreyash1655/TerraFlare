
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import {
  getRegions,
  getHotspots,
  getHotspotCells,
} from '../../../api/core';

type HotspotsData = Awaited<ReturnType<typeof getHotspots>>['data'];
type CellsData = Awaited<ReturnType<typeof getHotspotCells>>['data'];
type RegionsData = Awaited<ReturnType<typeof getRegions>>['data'];

type ActiveLayer = 'hex' | 'raw' | 'frp';

const MAP_STYLE =
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const formatNumber = (value: number | null | undefined) =>
  value == null
    ? '—'
    : value.toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      });

export default function HotspotMapPage() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [activeLayer, setActiveLayer] = useState<ActiveLayer>('hex');
  const [h3Res, setH3Res] = useState(7);
  const [showModis, setShowModis] = useState(true);
  const [showViirs, setShowViirs] = useState(true);

  const [selectedRegion, setSelectedRegion] = useState('pwn');
  const [selectedCellId, setSelectedCellId] = useState('');

  const [regions, setRegions] = useState<RegionsData['regions']>([]);
  const [hotspots, setHotspots] = useState<HotspotsData | null>(null);
  const [cells, setCells] = useState<CellsData | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const selectedCell = useMemo(
    () =>
      cells?.cells.find((cell) => cell.h3_cell === selectedCellId) ?? null,
    [cells, selectedCellId]
  );

  const region = regions.find(
    (item) => item.region_id === selectedRegion
  );

  const selectedSensors = useMemo(() => {
    const sensors: string[] = [];

    if (showModis) sensors.push('MODIS');
    if (showViirs) sensors.push('VIIRS');

    return sensors;
  }, [showModis, showViirs]);

  // Load regions and geospatial data.
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError('');

      try {
        const [regionResponse, hotspotResponse, cellResponse] =
          await Promise.all([
            getRegions(),
            getHotspots({
              region_id: selectedRegion,
              sensors: selectedSensors.join(','),
              limit: 10000,
            }),
            getHotspotCells({
              region_id: selectedRegion,
              h3_res: h3Res,
            }),
          ]);

        if (cancelled) return;

        setRegions(regionResponse.data.regions);
        setHotspots(hotspotResponse.data);
        setCells(cellResponse.data);

        setSelectedCellId((current) => {
          const stillExists = cellResponse.data.cells.some(
            (cell) => cell.h3_cell === current
          );

          return stillExists
            ? current
            : cellResponse.data.cells[0]?.h3_cell ?? '';
        });
      } catch (err) {
        if (cancelled) return;

        console.error('Failed to load hotspot data:', err);

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load geospatial data.'
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
      center: [-120, 45],
      zoom: 3,
      attributionControl: {
  compact: true,
},
    });

    map.addControl(
      new maplibregl.NavigationControl(),
      'top-right'
    );

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update map position when region changes.
  useEffect(() => {
    const map = mapRef.current;

    if (!map || !region?.bbox) return;

    const [west, south, east, north] = region.bbox;

    map.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      {
        padding: 70,
        duration: 1000,
        maxZoom: 8,
      }
    );
  }, [region]);

  // Add actual hotspot GeoJSON and update its styling.
  useEffect(() => {
    const map = mapRef.current;

    if (!map || !hotspots) return;

    const updateSourceAndLayer = () => {
      const existingSource = map.getSource(
        'terraflare-hotspots'
      ) as maplibregl.GeoJSONSource | undefined;

      if (existingSource) {
        existingSource.setData(hotspots);
      } else {
        map.addSource('terraflare-hotspots', {
          type: 'geojson',
          data: hotspots,
        });
      }

      if (!map.getLayer('terraflare-hotspot-points')) {
        map.addLayer({
          id: 'terraflare-hotspot-points',
          type: 'circle',
          source: 'terraflare-hotspots',
          paint: {
            'circle-radius': 5,
            'circle-color': '#fb923c',
            'circle-opacity': 0.85,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 0.5,
          },
        });

        map.on(
          'click',
          'terraflare-hotspot-points',
          (event: maplibregl.MapLayerMouseEvent) => {
            const feature = event.features?.[0];

            if (!feature) return;

            const geometry = feature.geometry;

            if (geometry.type !== 'Point') return;

            const coordinates = geometry.coordinates as [
              number,
              number
            ];

            const properties = feature.properties ?? {};

            const content = document.createElement('div');
            content.style.color = '#111827';
            content.style.fontFamily = 'monospace';
            content.style.fontSize = '12px';

            const fields = [
              ['Sensor', properties.sensor_family ?? 'Unknown'],
              ['Date', properties.acq_datetime_utc ?? '—'],
              ['Confidence', properties.confidence_class ?? '—'],
              ['FRP', `${properties.frp_mw ?? '—'} MW`],
            ];

            fields.forEach(([label, value]) => {
              const line = document.createElement('div');
              line.textContent = `${label}: ${value}`;
              content.appendChild(line);
            });

            const heading = document.createElement('strong');
            heading.textContent = 'Satellite Observation';
            content.prepend(heading);

            new maplibregl.Popup()
              .setLngLat(coordinates)
              .setDOMContent(content)
              .addTo(map);
          }
        );

        map.on('mouseenter', 'terraflare-hotspot-points', () => {
          map.getCanvas().style.cursor = 'pointer';
        });

        map.on('mouseleave', 'terraflare-hotspot-points', () => {
          map.getCanvas().style.cursor = '';
        });
      }

      // Update paint properties whenever the active layer changes.
      if (map.getLayer('terraflare-hotspot-points')) {
        if (activeLayer === 'frp') {
          map.setPaintProperty(
            'terraflare-hotspot-points',
            'circle-radius',
            [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'frp_mw'], 0],
              0, 3,
              50, 6,
              200, 10,
              500, 15,
            ]
          );

          map.setPaintProperty(
            'terraflare-hotspot-points',
            'circle-color',
            [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'frp_mw'], 0],
              0, '#7bd0ff',
              50, '#f59e0b',
              200, '#ff938c',
              500, '#ef4444',
            ]
          );
        } else {
          map.setPaintProperty(
            'terraflare-hotspot-points',
            'circle-radius',
            5
          );

          map.setPaintProperty(
            'terraflare-hotspot-points',
            'circle-color',
            [
              'match',
              ['get', 'sensor_family'],
              'MODIS', '#c084fc',
              'VIIRS', '#fb923c',
              '#7bd0ff',
            ]
          );
        }
      }
    };

    if (map.isStyleLoaded()) {
      updateSourceAndLayer();
    } else {
      map.once('load', updateSourceAndLayer);
    }

    return () => {
      map.off('load', updateSourceAndLayer);
    };
  }, [hotspots, activeLayer]);

  const handleCellSelect = useCallback((cellId: string) => {
    setSelectedCellId(cellId);
  }, []);

  const hotspotCount = hotspots?.features.length ?? 0;

  const modisCount =
    hotspots?.features.filter(
      (feature) => feature.properties?.sensor_family === 'MODIS'
    ).length ?? 0;

  const viirsCount =
    hotspots?.features.filter(
      (feature) => feature.properties?.sensor_family === 'VIIRS'
    ).length ?? 0;

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
            ['hex', 'Harmonized Cells'],
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

            {[6, 7, 8].map((res) => (
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
          <span>DETECTIONS: {formatNumber(hotspotCount)}</span>
          <span className="text-[#c084fc]">
            MODIS: {formatNumber(modisCount)}
          </span>
          <span className="text-[#fb923c]">
            VIIRS: {formatNumber(viirsCount)}
          </span>
        </div>
      </div>

      {/* Main map and inspector */}
      <div className="relative flex-1 min-h-[520px] bg-[#0B0F19]">
        <div
          ref={mapContainerRef}
          className="absolute inset-0"
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
              {activeLayer === 'hex'
                ? 'H3 CELL INSPECTOR'
                : 'MAP DATA INSPECTOR'}
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

              <div className="mt-3 grid grid-cols-2 gap-2 bg-[#171b26] p-3 rounded border border-[#262a35] font-caption-mono text-xs">
                <div>
                  <span className="text-[#a08e7a] text-[10px] block">
                    HARMONIZED VALUE
                  </span>
                  <span className="text-[#ffc174] font-bold">
                    {formatNumber(selectedCell.harmonized_value)}
                  </span>
                </div>

                <div>
                  <span className="text-[#a08e7a] text-[10px] block">
                    LOWER INTERVAL
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.lower)}
                  </span>
                </div>

                <div>
                  <span className="text-[#a08e7a] text-[10px] block">
                    UPPER INTERVAL
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.upper)}
                  </span>
                </div>

                <div>
                  <span className="text-[#a08e7a] text-[10px] block">
                    H3 RESOLUTION
                  </span>
                  <span className="text-[#7bd0ff] font-bold">
                    {cells?.h3_resolution ?? h3Res}
                  </span>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-caption-mono">
                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#c084fc] text-[10px]">
                    MODIS OBSERVED
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.modis_observed)}
                  </span>
                </div>

                <div className="p-2 rounded bg-[#171b26]">
                  <span className="block text-[#fb923c] text-[10px]">
                    VIIRS OBSERVED
                  </span>
                  <span className="text-[#dfe2f1] font-bold">
                    {formatNumber(selectedCell.viirs_observed)}
                  </span>
                </div>
              </div>
            </>
          )}

          {!isLoading && !error && !selectedCell && (
            <p className="text-xs text-[#a08e7a] py-6">
              No H3 cell records are available for this region and resolution.
            </p>
          )}

          <div className="mt-4 pt-3 border-t border-[#262a35]">
            <div className="font-caption-mono text-[10px] text-[#7bd0ff] mb-2">
              AVAILABLE H3 CELLS ({cells?.cells.length ?? 0})
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
                    <span>{formatNumber(cell.harmonized_value)}</span>
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
          Hotspot detections represent satellite-observed thermal anomalies,
          not confirmed unique fires. H3 values are displayed from the
          harmonized dataset; polygon geometry is not currently supplied by
          the cell API.
        </p>
      </div>
    </div>
  );
}

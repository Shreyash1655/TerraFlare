
import { useEffect, useRef } from 'react';
import type {
  Map as MapLibreMap,
  GeoJSONSource,
  MapMouseEvent,
} from 'maplibre-gl';

import type {
  Feature,
  FeatureCollection,
  Polygon,
} from 'geojson';

import { cellToBoundary } from 'h3-js';
import { getHotspotCells } from '../../api/core';

interface H3CellLayerProps {
  map: MapLibreMap | null;
  regionId: string;
  resolution?: number;
  selectedCell?: string;
  onSelectCell?: (cellId: string) => void;
  className?: string;
}

interface CellProperties {
  h3_cell: string;
  harmonized_value: number;
  lower: number;
  upper: number;
  modis_observed: number;
  viirs_observed: number;
  selected: boolean;
}

type CellCollection = FeatureCollection<Polygon, CellProperties>;

type CellFeature = Feature<Polygon, CellProperties>;

const SOURCE_ID = 'terraflare-h3-source';
const FILL_LAYER_ID = 'terraflare-h3-fill';
const BORDER_LAYER_ID = 'terraflare-h3-border';

export default function H3CellLayer({
  map,
  regionId,
  resolution = 7,
  selectedCell,
  onSelectCell,
}: H3CellLayerProps) {
  const geoJsonRef = useRef<CellCollection>({
    type: 'FeatureCollection',
    features: [],
  });

  const onSelectRef = useRef(onSelectCell);

  // Keep the latest selection callback.
  useEffect(() => {
    onSelectRef.current = onSelectCell;
  }, [onSelectCell]);

  // Fetch actual H3 cells from the backend.
  useEffect(() => {
    if (!map || !regionId) return;

    let cancelled = false;

    const fetchCells = async () => {
      try {
        const response = await getHotspotCells({
          region_id: regionId,
          h3_res: resolution,
        });

        if (cancelled) return;

        const features: CellFeature[] = response.data.cells.map((cell) => {
          const boundary = cellToBoundary(cell.h3_cell);

          // H3 returns [latitude, longitude].
          // GeoJSON requires [longitude, latitude].
          const coordinates: [number, number][] = boundary.map(
            ([lat, lng]) => [lng, lat]
          );

          // Close the polygon ring.
          if (coordinates.length > 0) {
            coordinates.push([...coordinates[0]]);
          }

          return {
            type: 'Feature',
            properties: {
              h3_cell: cell.h3_cell,
              harmonized_value: cell.harmonized_value,
              lower: cell.lower,
              upper: cell.upper,
              modis_observed: cell.modis_observed,
              viirs_observed: cell.viirs_observed,
              selected: cell.h3_cell === selectedCell,
            },
            geometry: {
              type: 'Polygon',
              coordinates: [coordinates],
            },
          };
        });

        const geoJson: CellCollection = {
          type: 'FeatureCollection',
          features,
        };

        geoJsonRef.current = geoJson;

        const source = map.getSource(SOURCE_ID) as
          | GeoJSONSource
          | undefined;

        source?.setData(geoJson);
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load H3 cells:', error);
        }
      }
    };

    fetchCells();

    return () => {
      cancelled = true;
    };
  }, [map, regionId, resolution, selectedCell]);

  // Create MapLibre source and visualization layers.
  useEffect(() => {
    if (!map) return;

    let disposed = false;
    let layersCreated = false;

    const handleCellClick = (event: MapMouseEvent) => {
      const features = map.queryRenderedFeatures(event.point, {
        layers: [FILL_LAYER_ID],
      });

      const cellId = features[0]?.properties?.h3_cell;

      if (typeof cellId === 'string') {
        onSelectRef.current?.(cellId);
      }
    };

    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = 'pointer';
    };

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = '';
    };

    const setupLayers = () => {
      if (disposed || !map.isStyleLoaded()) return;

      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, {
          type: 'geojson',
          data: geoJsonRef.current,
        });
      }

      if (!map.getLayer(FILL_LAYER_ID)) {
        map.addLayer({
          id: FILL_LAYER_ID,
          type: 'fill',
          source: SOURCE_ID,
          paint: {
            'fill-color': [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'harmonized_value'], 0],
              0, '#263548',
              50, '#facc15',
              150, '#f59e0b',
              300, '#ef4444',
              500, '#ff5b5b',
            ],
            'fill-opacity': [
              'case',
              ['boolean', ['get', 'selected'], false],
              0.85,
              0.55,
            ],
          },
        });
      }

      if (!map.getLayer(BORDER_LAYER_ID)) {
        map.addLayer({
          id: BORDER_LAYER_ID,
          type: 'line',
          source: SOURCE_ID,
          paint: {
            'line-color': [
              'case',
              ['boolean', ['get', 'selected'], false],
              '#7bd0ff',
              '#f59e0b',
            ],
            'line-width': [
              'case',
              ['boolean', ['get', 'selected'], false],
              2.5,
              0.8,
            ],
            'line-opacity': 0.9,
          },
        });
      }

      if (!layersCreated) {
        map.on('click', FILL_LAYER_ID, handleCellClick);
        map.on('mouseenter', FILL_LAYER_ID, handleMouseEnter);
        map.on('mouseleave', FILL_LAYER_ID, handleMouseLeave);
        layersCreated = true;
      }
    };

    if (map.isStyleLoaded()) {
      setupLayers();
    } else {
      map.once('load', setupLayers);
    }

    return () => {
      disposed = true;

      map.off('load', setupLayers);

      if (layersCreated) {
        map.off('click', FILL_LAYER_ID, handleCellClick);
        map.off('mouseenter', FILL_LAYER_ID, handleMouseEnter);
        map.off('mouseleave', FILL_LAYER_ID, handleMouseLeave);
      }

      if (map.getCanvas()) {
        map.getCanvas().style.cursor = '';
      }

      if (map.getLayer(BORDER_LAYER_ID)) {
        map.removeLayer(BORDER_LAYER_ID);
      }

      if (map.getLayer(FILL_LAYER_ID)) {
        map.removeLayer(FILL_LAYER_ID);
      }

      if (map.getSource(SOURCE_ID)) {
        map.removeSource(SOURCE_ID);
      }
    };
  }, [map]);

  // Update selected-cell highlighting without another API request.
  useEffect(() => {
    if (!map) return;

    const source = map.getSource(SOURCE_ID) as
      | GeoJSONSource
      | undefined;

    if (!source) return;

    const updatedFeatures = geoJsonRef.current.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        selected: feature.properties.h3_cell === selectedCell,
      },
    }));

    const updatedData: CellCollection = {
      type: 'FeatureCollection',
      features: updatedFeatures,
    };

    geoJsonRef.current = updatedData;
    source.setData(updatedData);
  }, [map, selectedCell]);

  return null;
}

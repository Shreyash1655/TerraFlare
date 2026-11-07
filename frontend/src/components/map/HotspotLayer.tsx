
import { useEffect, useRef } from 'react';
import type { Map as MapLibreMap, GeoJSONSource } from 'maplibre-gl';
import { getHotspots } from '../../api/core';

interface HotspotLayerProps {
  map: MapLibreMap | null;
  regionId: string;
  start?: string;
  end?: string;
  showModis?: boolean;
  showViirs?: boolean;
  className?: string;
}

const SOURCE_ID = 'terraflare-hotspots-source';
const VIIRS_LAYER_ID = 'terraflare-viirs-hotspots';
const MODIS_LAYER_ID = 'terraflare-modis-hotspots';

export default function HotspotLayer({
  map,
  regionId,
  start,
  end,
  showModis = true,
  showViirs = true,
}: HotspotLayerProps) {
  const geoJsonRef = useRef<GeoJSON.FeatureCollection>({
    type: 'FeatureCollection',
    features: [],
  });

  // Fetch actual hotspot observations.
  useEffect(() => {
    if (!map || !regionId) return;

    let cancelled = false;

    const fetchHotspots = async () => {
      try {
        const response = await getHotspots({
          region_id: regionId,
          start,
          end,
          sensors: 'MODIS,VIIRS',
        });

        if (cancelled) return;

        geoJsonRef.current = response.data;

        const source = map.getSource(SOURCE_ID) as
          | GeoJSONSource
          | undefined;

        source?.setData(geoJsonRef.current);
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load hotspot observations:', error);
        }
      }
    };

    fetchHotspots();

    return () => {
      cancelled = true;
    };
  }, [map, regionId, start, end]);

  // Create and manage MapLibre hotspot layers.
  useEffect(() => {
    if (!map) return;

    let disposed = false;

    const setupLayers = () => {
      if (disposed || !map.isStyleLoaded()) return;

      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, {
          type: 'geojson',
          data: geoJsonRef.current,
        });
      }

      if (!map.getLayer(VIIRS_LAYER_ID)) {
        map.addLayer({
          id: VIIRS_LAYER_ID,
          type: 'circle',
          source: SOURCE_ID,
          filter: ['==', ['get', 'sensor_family'], 'VIIRS'],
          paint: {
            'circle-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              2, 2,
              6, 4,
              10, 6,
            ],
            'circle-color': '#fb923c',
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 0.7,
            'circle-opacity': 0.9,
          },
          layout: {
            visibility: showViirs ? 'visible' : 'none',
          },
        });
      }

      if (!map.getLayer(MODIS_LAYER_ID)) {
        map.addLayer({
          id: MODIS_LAYER_ID,
          type: 'circle',
          source: SOURCE_ID,
          filter: ['==', ['get', 'sensor_family'], 'MODIS'],
          paint: {
            'circle-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              2, 3,
              6, 5,
              10, 7,
            ],
            'circle-color': 'rgba(192, 132, 252, 0.12)',
            'circle-stroke-color': '#c084fc',
            'circle-stroke-width': 1.8,
            'circle-opacity': 1,
          },
          layout: {
            visibility: showModis ? 'visible' : 'none',
          },
        });
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

      if (map.getLayer(VIIRS_LAYER_ID)) {
        map.removeLayer(VIIRS_LAYER_ID);
      }

      if (map.getLayer(MODIS_LAYER_ID)) {
        map.removeLayer(MODIS_LAYER_ID);
      }

      if (map.getSource(SOURCE_ID)) {
        map.removeSource(SOURCE_ID);
      }
    };
  }, [map]);

  // Toggle sensor visibility without fetching observations again.
  useEffect(() => {
    if (!map || !map.getLayer(VIIRS_LAYER_ID)) return;

    map.setLayoutProperty(
      VIIRS_LAYER_ID,
      'visibility',
      showViirs ? 'visible' : 'none'
    );
  }, [map, showViirs]);

  useEffect(() => {
    if (!map || !map.getLayer(MODIS_LAYER_ID)) return;

    map.setLayoutProperty(
      MODIS_LAYER_ID,
      'visibility',
      showModis ? 'visible' : 'none'
    );
  }, [map, showModis]);

  return null;
}

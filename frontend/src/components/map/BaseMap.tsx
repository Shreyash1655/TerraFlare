
import { useEffect, useRef, type ReactNode } from 'react';
import {
  Map as MapLibreMap,
  NavigationControl,
} from 'maplibre-gl';

import 'maplibre-gl/dist/maplibre-gl.css';

interface BaseMapProps {
  children?: ReactNode;
  center?: [number, number];
  zoom?: number;
  className?: string;
  onMapReady?: (map: MapLibreMap) => void;
}

export default function BaseMap({
  children,
  center = [0, 20],
  zoom = 2,
  className = '',
  onMapReady,
}: BaseMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onMapReadyRef = useRef(onMapReady);

  // Keep the latest callback without recreating the map.
  useEffect(() => {
    onMapReadyRef.current = onMapReady;
  }, [onMapReady]);

  // Initialize MapLibre once.
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new MapLibreMap({
      container: mapContainerRef.current,
      style:
        'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center,
      zoom,
    });

    map.addControl(
      new NavigationControl(),
      'top-right'
    );

    mapRef.current = map;

    // Share the map instance with child components.
    onMapReadyRef.current?.(map);

    return () => {
      map.remove();
      mapRef.current = null;
    };

    // Map initialization uses the initial center and zoom.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={`relative w-full h-full bg-[#0B0F19] overflow-hidden ${className}`}
    >
      {/* Interactive MapLibre Base Layer */}
      <div
        ref={mapContainerRef}
        className="absolute inset-0 w-full h-full"
      />

      {/* H3 Cells, Hotspots and HUD Overlays */}
      <div className="absolute inset-0 z-10 w-full h-full pointer-events-none">
        {children}
      </div>
    </div>
  );
}

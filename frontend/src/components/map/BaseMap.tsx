import { useRef, type ReactNode } from 'react';

interface BaseMapProps {
  children?: ReactNode;
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export default function BaseMap({
  children,
  className = '',
}: BaseMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);

  return (
    <div className={`relative w-full h-full bg-[#0B0F19] overflow-hidden ${className}`}>
      {/* Background Cartographic Layer */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full">
        {/* Graticule Grid */}
        <div className="absolute inset-0 bg-[radial-gradient(#7bd0ff_1px,transparent_1px)] [background-size:36px_36px] opacity-15 pointer-events-none"></div>
      </div>
      {/* Children Layer (Hexagons, Points, HUD) */}
      <div className="relative z-10 w-full h-full pointer-events-none">
        {children}
      </div>
    </div>
  );
}

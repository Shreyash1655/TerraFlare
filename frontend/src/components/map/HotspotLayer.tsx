interface HotspotLayerProps {
  showModis?: boolean;
  showViirs?: boolean;
  className?: string;
}

export default function HotspotLayer({
  showModis = true,
  showViirs = true,
  className = '',
}: HotspotLayerProps) {
  return (
    <svg
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
      preserveAspectRatio="none"
      viewBox="0 0 1000 600"
    >
      {/* VIIRS Hotspots: Orange Triangles */}
      {showViirs && (
        <g className="pointer-events-auto">
          <path d="M520,325 L525,334 L515,334 Z" fill="#fb923c" className="hover:scale-150 transition-transform cursor-pointer" />
          <path d="M535,330 L540,339 L530,339 Z" fill="#fb923c" className="hover:scale-150 transition-transform cursor-pointer" />
          <path d="M550,322 L555,331 L545,331 Z" fill="#fb923c" className="hover:scale-150 transition-transform cursor-pointer" />
          <path d="M500,280 L505,289 L495,289 Z" fill="#fb923c" className="hover:scale-150 transition-transform cursor-pointer" />
          <path d="M565,275 L570,284 L560,284 Z" fill="#fb923c" className="hover:scale-150 transition-transform cursor-pointer" />
        </g>
      )}

      {/* MODIS Hotspots: Purple Rings */}
      {showModis && (
        <g className="pointer-events-auto">
          <circle cx="530" cy="330" fill="none" r="6" stroke="#c084fc" strokeWidth="2" className="hover:scale-125 transition-transform cursor-pointer" />
          <circle cx="505" cy="285" fill="none" r="6" stroke="#c084fc" strokeWidth="2" className="hover:scale-125 transition-transform cursor-pointer" />
          <circle cx="482" cy="270" fill="none" r="6" stroke="#c084fc" strokeWidth="2" className="hover:scale-125 transition-transform cursor-pointer" />
        </g>
      )}
    </svg>
  );
}

interface H3CellLayerProps {
  resolution?: number;
  selectedCell?: string;
  onSelectCell?: (cellId: string) => void;
  className?: string;
}

export default function H3CellLayer({
  selectedCell = '872830828ffffff',
  onSelectCell,
  className = '',
}: H3CellLayerProps) {
  return (
    <svg
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
      preserveAspectRatio="none"
      viewBox="0 0 1000 600"
    >
      <defs>
        <radialGradient cx="50%" cy="50%" id="layerHexGlow" r="50%">
          <stop offset="0%" stopColor="#ff938c" stopOpacity="0.85"></stop>
          <stop offset="60%" stopColor="#f59e0b" stopOpacity="0.55"></stop>
          <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.05"></stop>
        </radialGradient>
      </defs>

      {/* Cluster Polygons */}
      <polygon
        fill="url(#layerHexGlow)"
        opacity="0.9"
        points="480,260 510,242 540,260 540,295 510,312 480,295"
        stroke="#ff938c"
        strokeWidth="1.5"
        className="pointer-events-auto cursor-pointer"
        onClick={() => onSelectCell?.('872830827ffffff')}
      ></polygon>

      <polygon
        fill="url(#layerHexGlow)"
        opacity="0.95"
        points="511,314 541,296 571,314 571,349 541,366 511,349"
        stroke="#ffbcb7"
        strokeWidth="2"
        className="pointer-events-auto cursor-pointer"
        onClick={() => onSelectCell?.('872830828ffffff')}
      ></polygon>

      {selectedCell === '872830828ffffff' && (
        <polygon
          className="animate-pulse pointer-events-none"
          fill="none"
          points="511,314 541,296 571,314 571,349 541,366 511,349"
          stroke="#7bd0ff"
          strokeDasharray="6,4"
          strokeWidth="2.5"
        ></polygon>
      )}
    </svg>
  );
}

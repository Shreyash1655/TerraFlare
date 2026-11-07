interface ProvenanceBadgeProps {
  sensor: 'MODIS' | 'VIIRS' | 'Harmonized' | 'H3';
  resolution?: string;
  className?: string;
}

export default function ProvenanceBadge({
  sensor,
  resolution,
  className = '',
}: ProvenanceBadgeProps) {
  switch (sensor) {
    case 'MODIS':
      return (
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#c084fc]/15 border border-[#a855f7]/40 text-[#c084fc] font-caption-mono text-[10px] font-bold uppercase tracking-wider ${className}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#c084fc]"></span>
          MODIS {resolution || '• 1KM'}
        </span>
      );
    case 'VIIRS':
      return (
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#fb923c]/15 border border-[#f97316]/40 text-[#fb923c] font-caption-mono text-[10px] font-bold uppercase tracking-wider ${className}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#fb923c]"></span>
          VIIRS {resolution || '• 375M'}
        </span>
      );
    case 'Harmonized':
      return (
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#f59e0b]/15 border border-[#f59e0b]/40 text-[#ffc174] font-caption-mono text-[10px] font-bold uppercase tracking-wider ${className}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#ffc174]"></span>
          Harmonized {resolution || '• H3-RES7'}
        </span>
      );
    case 'H3':
      return (
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#7bd0ff]/15 border border-[#00a6e0]/40 text-[#7bd0ff] font-caption-mono text-[10px] font-bold uppercase tracking-wider ${className}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#7bd0ff]"></span>
          H3 {resolution || 'RES 7'}
        </span>
      );
  }
}

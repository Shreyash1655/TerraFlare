
interface ProvenanceBadgeProps {
  sensor: 'MODIS' | 'VIIRS' | 'Harmonized' | 'H3';
  resolution?: string;
  className?: string;
}

const BADGE_STYLES = {
  MODIS: {
    container: 'bg-[#c084fc]/15 border-[#a855f7]/40 text-[#c084fc]',
    dot: 'bg-[#c084fc]',
  },
  VIIRS: {
    container: 'bg-[#fb923c]/15 border-[#f97316]/40 text-[#fb923c]',
    dot: 'bg-[#fb923c]',
  },
  Harmonized: {
    container: 'bg-[#f59e0b]/15 border-[#f59e0b]/40 text-[#ffc174]',
    dot: 'bg-[#ffc174]',
  },
  H3: {
    container: 'bg-[#7bd0ff]/15 border-[#00a6e0]/40 text-[#7bd0ff]',
    dot: 'bg-[#7bd0ff]',
  },
};

export default function ProvenanceBadge({
  sensor,
  resolution,
  className = '',
}: ProvenanceBadgeProps) {
  const style = BADGE_STYLES[sensor];

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-caption-mono text-[10px] font-bold uppercase tracking-wider ${style.container} ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${style.dot}`}
      />

      {sensor}

      {resolution && (
        <span className="opacity-80">
          • {resolution}
        </span>
      )}
    </span>
  );
}

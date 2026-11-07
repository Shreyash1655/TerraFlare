
interface UncertaintyNoteProps {
  intervalLevel?: number;
  note?: string;
  className?: string;
}

export default function UncertaintyNote({
  intervalLevel,
  note = 'Uncertainty bounds represent the range of values reported by the underlying harmonized dataset. Their interpretation depends on the documented methodology.',
  className = '',
}: UncertaintyNoteProps) {
  return (
    <div
      className={`flex items-start gap-2 p-2.5 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs text-[#a08e7a] ${className}`}
    >
      <span className="material-symbols-outlined text-[#7bd0ff] text-sm mt-0.5 shrink-0">
        info
      </span>

      <div className="leading-relaxed">
        {intervalLevel != null && (
          <span className="text-[#dfe2f1] font-semibold">
            {intervalLevel}% Interval: {' '}
          </span>
        )}

        {note}
      </div>
    </div>
  );
}

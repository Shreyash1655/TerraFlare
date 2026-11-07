interface UncertaintyNoteProps {
  intervalLevel?: number;
  note?: string;
  className?: string;
}

export default function UncertaintyNote({
  intervalLevel = 95,
  note = 'Shaded intervals reflect non-parametric residual bootstrap uncertainty from blocked temporal cross-validation.',
  className = '',
}: UncertaintyNoteProps) {
  return (
    <div
      className={`flex items-start gap-2 p-2.5 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs text-[#a08e7a] ${className}`}
    >
      <span className="material-symbols-outlined text-[#7bd0ff] text-sm mt-0.5 shrink-0">info</span>
      <div className="leading-relaxed">
        <span className="text-[#dfe2f1] font-semibold">±{intervalLevel}% Credible Interval: </span>
        {note}
      </div>
    </div>
  );
}

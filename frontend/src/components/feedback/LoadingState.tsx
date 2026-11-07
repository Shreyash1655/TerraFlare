interface LoadingStateProps {
  label?: string;
  sublabel?: string;
  className?: string;
}

export default function LoadingState({
  label = 'Querying In-Memory DuckDB Engine...',
  sublabel = 'Scanning partitioned Parquet observations and calibrating cell-day transfer tensors',
  className = '',
}: LoadingStateProps) {
  return (
    <div className={`w-full min-h-[220px] flex flex-col items-center justify-center p-8 text-center bg-[#1c1f2a]/60 rounded border border-[#262a35] ${className}`}>
      <div className="relative w-12 h-12 mb-4">
        <div className="absolute inset-0 rounded-full border-2 border-[#ffc174]/20 border-t-[#ffc174] animate-spin"></div>
        <div className="absolute inset-2 rounded-full border-2 border-[#7bd0ff]/20 border-b-[#7bd0ff] animate-spin [animation-duration:1.5s]"></div>
      </div>
      <div className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">{label}</div>
      <p className="font-caption-mono text-xs text-[#a08e7a] max-w-md">{sublabel}</p>
    </div>
  );
}

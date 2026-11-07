interface DataModeBannerProps {
  isSynthetic?: boolean;
  batchId?: string;
  className?: string;
}

export default function DataModeBanner({
  isSynthetic = true,
  batchId = 'ING-202611-042',
  className = '',
}: DataModeBannerProps) {
  if (!isSynthetic) return null;

  return (
    <aside
      aria-label="Dataset status"
      className={`w-full bg-[#0a0e18] px-6 py-1.5 flex flex-wrap items-center justify-between gap-2 border-b border-[#1F2937] ${className}`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-[#f59e0b] text-[#0B0F19] font-caption-mono text-[10px] uppercase tracking-wider font-bold">
          SYNTHETIC FIXTURE [ACTIVE]
        </span>
        <span className="font-caption-mono text-xs text-[#dfe2f1] truncate">
          Ingest batch #{batchId} • Overlap holdout validation active • DuckDB v1.1 WASM Partitioning
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="font-caption-mono text-[11px] text-[#a08e7a]">
          All figures illustrative for calibration benchmark
        </span>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#7bd0ff] animate-ping"></span>
          <span className="font-caption-mono text-[11px] text-[#7bd0ff] font-medium">PIPELINE VERIFIED</span>
        </div>
      </div>
    </aside>
  );
}

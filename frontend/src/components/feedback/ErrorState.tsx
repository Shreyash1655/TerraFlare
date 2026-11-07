interface ErrorStateProps {
  title?: string;
  message?: string;
  code?: string;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorState({
  title = 'Orbital Telemetry Stream Interrupted',
  message = 'Failed to execute analytical query against the observation repository.',
  code = 'QUERY_EXECUTION_FAILURE',
  onRetry,
  className = '',
}: ErrorStateProps) {
  return (
    <div className={`w-full min-h-[220px] flex flex-col items-center justify-center p-8 text-center bg-[#1c1f2a] rounded border border-[#ffb4ab]/30 ${className}`}>
      <div className="w-12 h-12 rounded bg-[#93000a]/20 border border-[#93000a]/50 flex items-center justify-center text-[#ffb4ab] mb-3">
        <span className="material-symbols-outlined text-2xl">warning</span>
      </div>
      <span className="font-caption-mono text-[10px] text-[#ffb4ab] uppercase font-bold tracking-wider mb-1">
        ERROR CODE: {code}
      </span>
      <h3 className="font-title-sm text-base font-bold text-[#dfe2f1] mb-1">{title}</h3>
      <p className="font-body-sm text-xs text-[#a08e7a] max-w-md mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-4 py-2 rounded bg-[#f59e0b] hover:bg-[#ffb95f] text-[#0B0F19] font-label-mono text-xs font-bold transition-colors"
          type="button"
        >
          <span className="material-symbols-outlined text-sm">refresh</span>
          Re-query Repository
        </button>
      )}
    </div>
  );
}

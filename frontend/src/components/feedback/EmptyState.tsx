interface EmptyStateProps {
  title?: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export default function EmptyState({
  title = 'No Thermal Hotspots Recorded in Domain',
  message = 'No active fire detections matched the current spatial bounds, sensor filter, or date window.',
  actionText,
  onAction,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`w-full min-h-[220px] flex flex-col items-center justify-center p-8 text-center bg-[#1c1f2a]/40 rounded border border-[#262a35] ${className}`}>
      <div className="w-12 h-12 rounded bg-[#171b26] border border-[#262a35] flex items-center justify-center text-[#7bd0ff] mb-3">
        <span className="material-symbols-outlined text-2xl">radar</span>
      </div>
      <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-1">{title}</h3>
      <p className="font-body-sm text-xs text-[#a08e7a] max-w-md mb-4">{message}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#262a35] hover:bg-[#313540] text-[#dfe2f1] font-label-mono text-xs transition-colors"
          type="button"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}

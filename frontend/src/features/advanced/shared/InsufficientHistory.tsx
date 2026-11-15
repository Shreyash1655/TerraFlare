import { useEffect, useState } from 'react';
import { getHistoryStatus, type HistoryStatusData } from '../../../api/advanced';

export default function InsufficientHistory({
  module,
  detail,
}: {
  module: string;
  detail?: string | null;
}) {
  const [s, setS] = useState<HistoryStatusData | null>(null);

  useEffect(() => {
    let active = true;
    getHistoryStatus()
      .then((r) => active && setS(r.data))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const m = s?.modules[module];

  return (
    <div className="p-6 rounded-lg bg-[#1c1f2a] border border-[#262a35]">
      <p className="text-[#ffc174] font-semibold text-sm">INSUFFICIENT EVIDENCE</p>
      <p className="text-[#dfe2f1] text-xs mt-2">
        {m?.message ?? 'This analysis needs more observation history than is currently loaded.'}
      </p>
      {s && (
        <dl className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 font-caption-mono text-xs">
          <div><dt className="text-[#a08e7a] text-[10px]">REQUIRED</dt><dd className="text-[#dfe2f1]">{m ? `${m.required_years} years` : '—'}</dd></div>
          <div><dt className="text-[#a08e7a] text-[10px]">AVAILABLE</dt><dd className="text-[#dfe2f1]">{s.available_days} days</dd></div>
          <div><dt className="text-[#a08e7a] text-[10px]">DATE RANGE</dt><dd className="text-[#dfe2f1]">{s.date_range[0] ?? '—'} to {s.date_range[1] ?? '—'}</dd></div>
          <div><dt className="text-[#a08e7a] text-[10px]">SOURCE</dt><dd className="text-[#dfe2f1]">{s.source}{s.is_synthetic ? ' (synthetic)' : ''}</dd></div>
        </dl>
      )}
      <p className="text-[#a08e7a] text-[10px] font-caption-mono mt-3">
        No baseline is estimated or substituted. Load multi-year standard-processing (SP) FIRMS data to enable this page.
      </p>
      {detail && <p className="text-[#a08e7a] text-[10px] font-caption-mono mt-1">Server message: {detail}</p>}
    </div>
  );
}
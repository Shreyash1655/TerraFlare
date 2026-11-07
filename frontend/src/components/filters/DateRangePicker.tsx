interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
  className?: string;
}

export default function DateRangePicker({
  startDate,
  endDate,
  onChange,
  className = '',
}: DateRangePickerProps) {
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35] ${className}`}>
      <span className="material-symbols-outlined text-[#f59e0b] text-sm">date_range</span>
      <div className="flex flex-col">
        <span className="font-caption-mono text-[9px] text-[#a08e7a] leading-none mb-0.5">OBSERVATION WINDOW</span>
        <div className="flex items-center gap-1 font-label-mono text-xs text-[#dfe2f1]">
          <input
            type="date"
            value={startDate}
            onChange={(e) => onChange(e.target.value, endDate)}
            className="bg-transparent text-[#dfe2f1] text-xs focus:outline-none cursor-pointer"
          />
          <span className="text-[#a08e7a]">–</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => onChange(startDate, e.target.value)}
            className="bg-transparent text-[#dfe2f1] text-xs focus:outline-none cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}

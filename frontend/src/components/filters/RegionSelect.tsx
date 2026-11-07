interface RegionSelectProps {
  value: string;
  onChange: (regionId: string) => void;
  className?: string;
}

const REGIONS = [
  { id: 'pwn', name: 'Western North America (PacNW)', coords: '44.1°N, -121.8°W' },
  { id: 'amz', name: 'Amazon Basin Arc', coords: '-9.5°S, -62.8°W' },
  { id: 'sib', name: 'Siberian Boreal Larch Taiga', coords: '62.0°N, 129.7°E' },
  { id: 'aus', name: 'SE Australia Eurobodalla / NSW', coords: '-35.7°S, 150.1°E' },
];

export default function RegionSelect({ value, onChange, className = '' }: RegionSelectProps) {
  return (
    <div className={`flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35] ${className}`}>
      <span className="material-symbols-outlined text-[#7bd0ff] text-sm">location_on</span>
      <div className="flex flex-col">
        <span className="font-caption-mono text-[9px] text-[#a08e7a] leading-none mb-0.5">TARGET DOMAIN</span>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer pr-1"
        >
          {REGIONS.map((r) => (
            <option key={r.id} value={r.id} className="bg-[#171b26] text-[#dfe2f1]">
              {r.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

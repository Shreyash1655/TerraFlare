import { useFilters } from '../../hooks/useFilters';
import Button from '../ui/Button';

const REGIONS = [
  { id: 'pwn', name: 'Western North America • PacNW' },
  { id: 'amz', name: 'Amazon Basin Arc' },
  { id: 'sib', name: 'Siberian Boreal Zone' },
  { id: 'aus', name: 'SE Australia Eurobodalla' },
];

export default function FilterBar() {
  const { filters, updateFilters } = useFilters();

  return (
    <div className="w-full px-4 py-2 bg-[#111827] border-b border-[#1F2937] flex-shrink-0 flex flex-wrap items-center justify-between gap-4">
      <div className="flex flex-wrap items-center gap-2">
        {/* Target Domain Selector */}
        <div className="flex items-center gap-2 bg-[#1A2234] border border-[#374151] px-2 py-1.5 rounded">
          <span className="material-symbols-outlined text-[#7bd0ff] text-sm">location_on</span>
          <div className="flex flex-col">
            <span className="font-caption-mono text-[9px] text-[#9CA3AF] leading-none mb-0.5">TARGET DOMAIN</span>
            <select
              value={filters.regionId}
              onChange={(e) => updateFilters({ regionId: e.target.value })}
              className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
            >
              {REGIONS.map((r) => (
                <option key={r.id} value={r.id} className="bg-[#1A2234] text-[#dfe2f1]">
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Temporal Window Selector */}
        <div className="flex items-center gap-2 bg-[#1A2234] border border-[#374151] px-2 py-1.5 rounded">
          <span className="material-symbols-outlined text-[#f59e0b] text-sm">date_range</span>
          <div className="flex flex-col">
            <span className="font-caption-mono text-[9px] text-[#9CA3AF] leading-none mb-0.5">SENSOR OVERLAP</span>
            <div className="flex items-center gap-1 font-label-mono text-xs text-[#dfe2f1]">
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => updateFilters({ startDate: e.target.value })}
                className="bg-transparent text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              />
              <span className="text-[#9CA3AF]">–</span>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => updateFilters({ endDate: e.target.value })}
                className="bg-transparent text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
              />
            </div>
          </div>
          <span className="px-1 py-0.5 rounded bg-[#374151] text-[#f59e0b] font-caption-mono text-[10px] ml-1">
            5.0 Yrs
          </span>
        </div>

        {/* H3 Spatial Index */}
        <div className="flex items-center gap-2 bg-[#1A2234] border border-[#374151] px-2 py-1.5 rounded">
          <span className="material-symbols-outlined text-[#7bd0ff] text-sm">hexagon</span>
          <div className="flex flex-col">
            <span className="font-caption-mono text-[9px] text-[#9CA3AF] leading-none mb-0.5">SPATIAL INDEX</span>
            <span className="font-label-mono text-xs text-[#dfe2f1]">H3 Hex Res {filters.h3Res} (~5.1 km²)</span>
          </div>
        </div>

        {/* Confidence Selector */}
        <div className="flex items-center gap-2 bg-[#1A2234] border border-[#374151] px-2 py-1.5 rounded">
          <span className="material-symbols-outlined text-[#9CA3AF] text-sm">verified_user</span>
          <div className="flex flex-col">
            <span className="font-caption-mono text-[9px] text-[#9CA3AF] leading-none mb-0.5">FIRMS CONFIDENCE</span>
            <select
              value={filters.minConfidence}
              onChange={(e) => updateFilters({ minConfidence: e.target.value as 'all' | 'nominal' | 'high' })}
              className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer"
            >
              <option value="nominal" className="bg-[#1A2234]">Nominal + High (&gt;50%)</option>
              <option value="high" className="bg-[#1A2234]">High Only (&gt;80%)</option>
              <option value="all" className="bg-[#1A2234]">All Classes (Include Low)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Diurnal Pass Profile */}
      <div className="flex items-center gap-2">
        <span className="font-caption-mono text-[10px] text-[#9CA3AF] uppercase">Pass Profile:</span>
        <div className="flex items-center bg-[#1A2234] border border-[#374151] p-0.5 rounded">
          {(['all', 'day', 'night'] as const).map((pass) => (
            <button
              key={pass}
              type="button"
              onClick={() => updateFilters({ passProfile: pass })}
              className={`px-2 py-0.5 rounded font-label-mono text-xs transition-colors ${
                filters.passProfile === pass
                  ? 'bg-[#7bd0ff] text-[#00354a] font-bold'
                  : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
              }`}
            >
              {pass === 'all' ? 'All Passes' : pass === 'day' ? 'Day Only' : 'Night (MWIR)'}
            </button>
          ))}
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon="refresh"
          className="ml-1"
          title="Reload DuckDB Query Cache"
          onClick={() => window.location.reload()}
        />
      </div>
    </div>
  );
}

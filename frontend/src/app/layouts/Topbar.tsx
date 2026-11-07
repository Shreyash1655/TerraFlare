import { NavLink } from 'react-router-dom';

const navTabs = [
  { path: '/', label: 'Geospatial Map' },
  { path: '/comparison', label: 'Harmonization & Calibration' },
  { path: '/calendar', label: 'Climatology Calendar' },
  { path: '/advanced/season-shift', label: 'Advanced Intelligence' },
  { path: '/advanced/quality', label: 'Quality & Pipeline' },
];

export default function Topbar() {
  return (
    <header className="flex-shrink-0 z-50 bg-[#0B0F19] border-b border-[#1F2937]">
      <div className="h-16 w-full px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#1A2234] flex items-center justify-center border border-[#374151]">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[20px]">public</span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-headline-sm text-lg font-semibold tracking-tight text-[#ffc174]">TerraFlare</span>
              <span className="text-[#9CA3AF] font-label-mono text-[10px] uppercase tracking-wider hidden md:block">
                NASA Space Apps 2026 • MODIS & VIIRS Harmonization v1.0
              </span>
            </div>
          </div>
        </div>

        <div className="hidden lg:flex flex-col items-center justify-center">
          <div className="flex items-center gap-2 px-2 py-0.5 rounded bg-[#f59e0b]/20 border border-[#f59e0b]/50">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] animate-pulse"></span>
            <span className="text-[#f59e0b] font-caption-mono text-[10px] font-bold tracking-wider">SYNTHETIC DATA FIXTURE [ACTIVE]</span>
          </div>
          <span className="text-[#9CA3AF] font-caption-mono text-[9px] mt-0.5">DUCKDB v1.1 • IN-MEMORY</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden xl:flex items-center gap-2 bg-[#1A2234] px-3 py-1.5 rounded border border-[#374151]">
            <span className="material-symbols-outlined text-[#7bd0ff] text-sm">public</span>
            <select className="bg-transparent text-[#dfe2f1] font-label-mono text-xs focus:outline-none cursor-pointer">
              <option className="bg-[#1A2234]" value="pwn">Western North America - Pacific NW</option>
              <option className="bg-[#1A2234]" value="amz">Amazon Basin Tropical</option>
              <option className="bg-[#1A2234]" value="sib">Siberian Boreal Zone</option>
              <option className="bg-[#1A2234]" value="aus">SE Australia Eurobodalla</option>
            </select>
          </div>
          <div className="hidden md:flex flex-col text-right">
            <span className="font-caption-mono text-[10px] text-[#9CA3AF]">DuckDB: 4.8M rows</span>
            <span className="font-caption-mono text-[10px] text-[#7bd0ff] flex items-center justify-end gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#7bd0ff] animate-pulse"></span>
              Sync: 24ms
            </span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#1A2234] border border-[#374151] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#9CA3AF] text-[16px]">person</span>
          </div>
        </div>
      </div>

      {/* Primary horizontal navigation tabs matching Stitch prototype */}
      <nav className="w-full px-6 bg-[#0a0e18] flex items-center gap-6 overflow-x-auto border-t border-[#1F2937]">
        {navTabs.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            end={tab.path === '/'}
            className={({ isActive }) =>
              `pb-2.5 pt-2 font-title-sm text-xs font-semibold tracking-wide transition-colors whitespace-nowrap border-b-2 ${
                isActive
                  ? 'text-[#ffc174] border-[#ffc174]'
                  : 'text-[#9CA3AF] border-transparent hover:text-[#dfe2f1]'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

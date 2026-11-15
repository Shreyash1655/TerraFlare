import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { getHealth } from '../../api/core';

const navTabs = [
  { path: '/', label: 'Geospatial Map' },
  { path: '/comparison', label: 'Harmonization & Calibration' },
  { path: '/calendar', label: 'Climatology Calendar' },
  { path: '/advanced/season-shift', label: 'Advanced Intelligence' },
  { path: '/advanced/quality', label: 'Quality & Pipeline' },
];

export default function Topbar() {
  const [mode, setMode] = useState<{ label: string; synthetic: boolean } | null>(null);
  useEffect(() => {
    let off = false;
    getHealth()
      .then((r) => { if (!off) setMode({ label: r.data.data_mode, synthetic: !!r.data.is_synthetic }); })
      .catch(() => { if (!off) setMode(null); });
    return () => { off = true; };
  }, []);
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
                NASA Space Apps 2026 · MODIS &amp; VIIRS Harmonization v1.0
              </span>
            </div>
          </div>
        </div>

        <div className="hidden lg:flex flex-col items-center justify-center">
          {mode?.synthetic ? (
            <div className="flex items-center gap-2 px-2 py-0.5 rounded bg-[#f59e0b]/20 border border-[#f59e0b]/50">
              <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] animate-pulse"></span>
              <span className="text-[#f59e0b] font-caption-mono text-[10px] font-bold tracking-wider">SYNTHETIC DATA FIXTURE [ACTIVE]</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2 py-0.5 rounded bg-[#10b981]/15 border border-[#10b981]/40">
              <span className="text-[#10b981] font-caption-mono text-[10px] font-bold tracking-wider">
                {mode ? `REAL DATA MODE (${mode.label})` : 'DATA MODE UNKNOWN'}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex flex-col text-right">
            <span className="font-caption-mono text-[10px] text-[#9CA3AF]">Source: see Provenance panel</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#1A2234] border border-[#374151] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#9CA3AF] text-[16px]">person</span>
          </div>
        </div>
      </div>

      {/* Primary horizontal navigation tabs */}
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
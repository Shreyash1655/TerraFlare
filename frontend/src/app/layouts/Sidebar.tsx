import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { path: '/map', label: 'Geospatial Map', icon: 'map' },
  { path: '/comparison', label: 'Harmonization', icon: 'compare' },
  { path: '/calendar', label: 'Activity Calendar', icon: 'calendar_month' },
  { path: '/advanced/season-shift', label: 'Advanced Intel', icon: 'memory' },
  { path: '/advanced/quality', label: 'Quality & Pipeline', icon: 'analytics' },
];

export default function Sidebar() {
  return (
    <aside className="w-16 hover:w-64 transition-all duration-300 ease-in-out bg-[#0B0F19] border-r border-[#1F2937] flex flex-col group overflow-hidden shrink-0 z-40">
      <div className="flex flex-col gap-2 p-3 mt-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-4 px-3 py-2.5 rounded transition-colors whitespace-nowrap ${isActive
                ? 'bg-[#ffc174]/10 text-[#ffc174] border border-[#ffc174]/30'
                : 'text-[#9CA3AF] hover:text-[#dfe2f1] hover:bg-[#1A2234]'
              }`
            }
          >
            <span className="material-symbols-outlined text-[20px] shrink-0">{item.icon}</span>
            <span className="font-title-sm text-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              {item.label}
            </span>
          </NavLink>
        ))}
      </div>

      <div className="mt-auto p-4 mb-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="font-caption-mono text-[9px] text-[#9CA3AF] uppercase tracking-wider mb-2">System Status</div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></div>
          <span className="font-label-mono text-xs text-[#10B981]">Pipeline Online</span>
        </div>
      </div>
    </aside>
  );
}
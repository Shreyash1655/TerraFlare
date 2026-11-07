interface Tab {
  id: string;
  label: string;
  count?: number | string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({ tabs, activeTab, onChange, className = '' }: TabsProps) {
  return (
    <div className={`flex items-center gap-1 border-b border-[#1F2937] ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3 py-2 font-label-mono text-[11px] transition-colors border-b-2 ${isActive
                ? 'text-[#F9FAFB] border-[#38BDF8]'
                : 'text-[#9CA3AF] border-transparent hover:text-[#F9FAFB]'
              }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className={`px-1.5 py-0.5 rounded font-caption-mono text-[9px] ${isActive ? 'bg-[#38BDF8]/20 text-[#38BDF8]' : 'bg-[#1F2937] text-[#9CA3AF]'
                }`}>
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
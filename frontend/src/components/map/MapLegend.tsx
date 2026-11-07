
interface MapLegendProps {
  className?: string;
}

export default function MapLegend({ className = '' }: MapLegendProps) {
  return (
    <div
      className={`bg-[#171b26]/90 backdrop-blur-md px-3.5 py-2.5 rounded border border-[#1F2937] flex flex-col gap-2 font-caption-mono text-xs ${className}`}
    >
      <div className="flex items-center justify-between gap-4">
        <span className="text-[#a08e7a] uppercase text-[10px]">
          Harmonized Hotspot Activity
        </span>
        <span className="text-[#dfe2f1]">
          Relative value
        </span>
      </div>

      {/* H3 activity color scale */}
      <div className="w-56 h-2 rounded-full bg-gradient-to-r from-[#263548] via-[#f59e0b] to-[#ff5b5b]" />

      <div className="flex justify-between text-[10px] text-[#a08e7a]">
        <span>0</span>
        <span>150</span>
        <span>300</span>
        <span>500+</span>
      </div>

      {/* Sensor and spatial layer legend */}
      <div className="pt-2 border-t border-[#262a35] flex flex-wrap items-center justify-between gap-2 text-[10px]">
        <span className="flex items-center gap-1 text-[#fb923c]">
          <span className="w-2 h-2 rounded-full bg-[#fb923c] inline-block" />
          VIIRS
        </span>

        <span className="flex items-center gap-1 text-[#c084fc]">
          <span className="w-2 h-2 rounded-full border border-[#c084fc] inline-block" />
          MODIS
        </span>

        <span className="flex items-center gap-1 text-[#ffc174]">
          <span className="w-2 h-2 rounded-sm bg-[#ffc174] inline-block" />
          H3 Cell
        </span>
      </div>

      <p className="text-[9px] text-[#a08e7a] leading-relaxed">
        Color represents harmonized activity values. Sensor markers
        represent individual satellite detections.
      </p>
    </div>
  );
}

interface MapLegendProps {
  className?: string;
}

export default function MapLegend({ className = '' }: MapLegendProps) {
  return (
    <div
      className={`bg-[#171b26]/90 backdrop-blur-md px-3.5 py-2.5 rounded border border-[#1F2937] flex flex-col gap-2 font-caption-mono text-xs ${className}`}
    >
      <div className="flex items-center justify-between gap-4">
        <span className="text-[#a08e7a] uppercase text-[10px]">Thermal Radiance Flux Density</span>
        <span className="text-[#dfe2f1]">0 → &gt;120 MW/km²</span>
      </div>
      <div className="w-56 h-2 rounded-full bg-gradient-to-r from-[#313540] via-[#7bd0ff] to-[#ff938c]"></div>
      <div className="flex justify-between text-[10px] text-[#a08e7a]">
        <span>Low (0.1)</span>
        <span>Nominal (45.0)</span>
        <span>Critical (&gt;100)</span>
      </div>
      <div className="pt-2 border-t border-[#262a35] flex items-center justify-between text-[10px]">
        <span className="flex items-center gap-1 text-[#fb923c]">
          <span className="w-2 h-2 rounded-sm bg-[#fb923c] inline-block"></span>VIIRS 375m
        </span>
        <span className="flex items-center gap-1 text-[#c084fc]">
          <span className="w-2 h-2 rounded-full border border-[#c084fc] inline-block"></span>MODIS 1km
        </span>
        <span className="flex items-center gap-1 text-[#ffc174]">
          <span className="w-2 h-2 rounded-xs bg-[#ffc174] inline-block"></span>Harmonized Hex
        </span>
      </div>
    </div>
  );
}

interface SensorToggleProps {
  sensors: string[];
  onChange: (sensors: string[]) => void;
  className?: string;
}

export default function SensorToggle({ sensors, onChange, className = '' }: SensorToggleProps) {
  const toggleSensor = (sensor: string) => {
    if (sensors.includes(sensor)) {
      if (sensors.length === 1) return; // Prevent empty selection
      onChange(sensors.filter((s) => s !== sensor));
    } else {
      onChange([...sensors, sensor]);
    }
  };

  return (
    <div className={`flex items-center bg-[#171b26] p-0.5 rounded border border-[#262a35] ${className}`}>
      <button
        type="button"
        onClick={() => toggleSensor('MODIS')}
        className={`px-2.5 py-1 rounded font-caption-mono text-xs transition-colors ${
          sensors.includes('MODIS')
            ? 'bg-[#c084fc]/20 text-[#c084fc] font-bold border border-[#c084fc]/40'
            : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
        }`}
      >
        MODIS (1km)
      </button>
      <button
        type="button"
        onClick={() => toggleSensor('VIIRS')}
        className={`px-2.5 py-1 rounded font-caption-mono text-xs transition-colors ${
          sensors.includes('VIIRS')
            ? 'bg-[#fb923c]/20 text-[#fb923c] font-bold border border-[#fb923c]/40'
            : 'text-[#9CA3AF] hover:text-[#dfe2f1]'
        }`}
      >
        VIIRS (375m)
      </button>
    </div>
  );
}

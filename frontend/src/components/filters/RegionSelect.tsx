
import { useEffect, useState } from 'react';
import { getRegions } from '../../api/core';

interface Region {
  region_id: string;
  name: string;
  bbox: number[];
}

interface RegionSelectProps {
  value: string;
  onChange: (regionId: string) => void;
  className?: string;
}

export default function RegionSelect({
  value,
  onChange,
  className = '',
}: RegionSelectProps) {
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchRegions = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await getRegions();

        if (!isMounted) return;

        const availableRegions = response.data.regions;
        setRegions(availableRegions);

        // Select the first available region if the current selection
        // is not present in the API response.
        if (
          availableRegions.length > 0 &&
          !availableRegions.some((region) => region.region_id === value)
        ) {
          onChange(availableRegions[0].region_id);
        }
      } catch (err) {
        if (!isMounted) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load available regions.'
        );
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchRegions();

    return () => {
      isMounted = false;
    };
  }, [value, onChange]);

  return (
    <div
      className={`flex items-center gap-1.5 px-3 py-1.5 bg-[#171b26] rounded border border-[#262a35] ${className}`}
    >
      <span className="material-symbols-outlined text-[#7bd0ff] text-sm">
        location_on
      </span>

      <div className="flex flex-col">
        <span className="font-caption-mono text-[9px] text-[#a08e7a] leading-none mb-0.5">
          TARGET DOMAIN
        </span>

        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={loading || !!error || regions.length === 0}
          className="bg-transparent font-label-mono text-xs text-[#dfe2f1] focus:outline-none cursor-pointer pr-1 disabled:opacity-50"
        >
          {loading && <option value="">Loading regions...</option>}

          {error && <option value="">Regions unavailable</option>}

          {!loading && !error && regions.length === 0 && (
            <option value="">No regions available</option>
          )}

          {regions.map((region) => (
            <option
              key={region.region_id}
              value={region.region_id}
              className="bg-[#171b26] text-[#dfe2f1]"
            >
              {region.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

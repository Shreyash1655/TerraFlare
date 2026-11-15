import { useEffect, useState } from 'react';

export type Sensor = 'viirs' | 'modis';

export interface Scope {
  bbox: string;
  start: string;
  end: string;
  sensor: Sensor;
}

export const INDIA_BBOX = '68,6,98,36';

export function isCapError(message: string | null): boolean {
  return !!message && /too_many|too many|limit|narrow/i.test(message);
}

export function scopeToParams(scope: Scope) {
  return {
    bbox: scope.bbox || undefined,
    start: scope.start || undefined,
    end: scope.end || undefined,
    sensor: scope.sensor,
  };
}

interface Props {
  scope: Scope;
  minDate?: string | null;
  maxDate?: string | null;
  disabled?: boolean;
  onApply: (scope: Scope) => void;
}

export default function ScopeControls({
  scope,
  minDate,
  maxDate,
  disabled,
  onApply,
}: Props) {
  const [draft, setDraft] = useState<Scope>(scope);

  useEffect(() => {
    setDraft(scope);
  }, [scope]);

  const field =
    'bg-[#0a0e18] border border-[#262a35] rounded px-2 py-1.5 text-xs font-caption-mono text-[#dfe2f1]';

  return (
    <div className="p-4 rounded-lg bg-[#1c1f2a] border border-[#262a35]">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-caption-mono text-[#a08e7a]">
            FROM
          </span>
          <input
            type="date"
            className={field}
            value={draft.start}
            min={minDate ?? undefined}
            max={maxDate ?? undefined}
            onChange={(e) => setDraft({ ...draft, start: e.target.value })}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-caption-mono text-[#a08e7a]">
            TO
          </span>
          <input
            type="date"
            className={field}
            value={draft.end}
            min={minDate ?? undefined}
            max={maxDate ?? undefined}
            onChange={(e) => setDraft({ ...draft, end: e.target.value })}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-caption-mono text-[#a08e7a]">
            SENSOR (ONE AT A TIME)
          </span>
          <select
            className={field}
            value={draft.sensor}
            onChange={(e) =>
              setDraft({ ...draft, sensor: e.target.value as Sensor })
            }
          >
            <option value="viirs">VIIRS</option>
            <option value="modis">MODIS</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 grow min-w-[220px]">
          <span className="text-[10px] font-caption-mono text-[#a08e7a]">
            BOUNDING BOX (min_lon,min_lat,max_lon,max_lat)
          </span>
          <input
            type="text"
            className={field}
            placeholder="empty = global"
            value={draft.bbox}
            onChange={(e) => setDraft({ ...draft, bbox: e.target.value })}
          />
        </label>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setDraft({ ...draft, bbox: INDIA_BBOX })}
            className="px-3 py-1.5 rounded bg-[#262a35] text-[#7bd0ff] text-xs font-bold"
          >
            India preset
          </button>
          <button
            type="button"
            onClick={() => setDraft({ ...draft, bbox: '' })}
            className="px-3 py-1.5 rounded bg-[#262a35] text-[#a08e7a] text-xs font-bold"
          >
            Global
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onApply(draft)}
            className="px-4 py-1.5 rounded bg-[#ffc174] text-[#0a0e18] text-xs font-bold disabled:opacity-50"
          >
            Apply
          </button>
        </div>
      </div>

      <p className="mt-2 text-[10px] font-caption-mono text-[#a08e7a]">
        The dataset is global. A single day can exceed the 50,000-point safety
        limit, so narrow the box or the dates if you see a limit message.
      </p>
    </div>
  );
}
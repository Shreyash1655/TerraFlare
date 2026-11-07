
import { useSearchParams } from 'react-router-dom';
import { useCallback, useMemo } from 'react';

export interface FilterState {
  regionId: string;
  startDate: string;
  endDate: string;
  sensors: string[];
  passProfile: 'all' | 'day' | 'night';
  minConfidence: 'all' | 'nominal' | 'high';
  h3Res: number;
}

const VALID_SENSORS = ['MODIS', 'VIIRS'];

const VALID_PASS_PROFILES = ['all', 'day', 'night'] as const;

const VALID_CONFIDENCE = ['all', 'nominal', 'high'] as const;

const DEFAULT_SENSORS = ['MODIS', 'VIIRS'];

const DEFAULT_H3_RESOLUTION = 7;

const MIN_H3_RESOLUTION = 0;
const MAX_H3_RESOLUTION = 15;

function isValidDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }

  const date = new Date(`${value}T00:00:00Z`);

  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
  );
}

function parseSensors(value: string | null): string[] {
  if (value === null) {
    return [...DEFAULT_SENSORS];
  }

  const sensors = value
    .split(',')
    .map((sensor) => sensor.trim().toUpperCase())
    .filter((sensor) => VALID_SENSORS.includes(sensor));

  return [...new Set(sensors)];
}

function parsePassProfile(
  value: string | null
): FilterState['passProfile'] {
  if (
    value &&
    VALID_PASS_PROFILES.includes(
      value as FilterState['passProfile']
    )
  ) {
    return value as FilterState['passProfile'];
  }

  return 'all';
}

function parseConfidence(
  value: string | null
): FilterState['minConfidence'] {
  if (
    value &&
    VALID_CONFIDENCE.includes(
      value as FilterState['minConfidence']
    )
  ) {
    return value as FilterState['minConfidence'];
  }

  return 'nominal';
}

function parseResolution(value: string | null): number {
  if (value === null || value.trim() === '') {
    return DEFAULT_H3_RESOLUTION;
  }

  const resolution = Number(value);

  if (
    !Number.isInteger(resolution) ||
    resolution < MIN_H3_RESOLUTION ||
    resolution > MAX_H3_RESOLUTION
  ) {
    return DEFAULT_H3_RESOLUTION;
  }

  return resolution;
}

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: FilterState = useMemo(() => {
    const regionId = searchParams.get('region') || '';

    const rawStartDate = searchParams.get('start') || '';
    const rawEndDate = searchParams.get('end') || '';

    const validStartDate = isValidDate(rawStartDate)
      ? rawStartDate
      : '';

    const validEndDate = isValidDate(rawEndDate)
      ? rawEndDate
      : '';

    // Avoid an invalid date range.
    const datesAreValid =
      !validStartDate ||
      !validEndDate ||
      validStartDate <= validEndDate;

    return {
      regionId,
      startDate: datesAreValid ? validStartDate : '',
      endDate: datesAreValid ? validEndDate : '',
      sensors: parseSensors(searchParams.get('sensors')),
      passProfile: parsePassProfile(searchParams.get('pass')),
      minConfidence: parseConfidence(searchParams.get('conf')),
      h3Res: parseResolution(searchParams.get('res')),
    };
  }, [searchParams]);

  const updateFilters = useCallback(
    (newFilters: Partial<FilterState>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          if (newFilters.regionId !== undefined) {
            if (newFilters.regionId.trim()) {
              next.set('region', newFilters.regionId.trim());
            } else {
              next.delete('region');
            }
          }

          if (newFilters.startDate !== undefined) {
            if (isValidDate(newFilters.startDate)) {
              next.set('start', newFilters.startDate);
            } else {
              next.delete('start');
            }
          }

          if (newFilters.endDate !== undefined) {
            if (isValidDate(newFilters.endDate)) {
              next.set('end', newFilters.endDate);
            } else {
              next.delete('end');
            }
          }

          if (newFilters.sensors !== undefined) {
            const sensors = [
              ...new Set(
                newFilters.sensors
                  .map((sensor) => sensor.toUpperCase())
                  .filter((sensor) => VALID_SENSORS.includes(sensor))
              ),
            ];

            if (sensors.length > 0) {
              next.set('sensors', sensors.join(','));
            } else {
              next.set('sensors', '');
            }
          }

          if (newFilters.passProfile !== undefined) {
            next.set(
              'pass',
              VALID_PASS_PROFILES.includes(newFilters.passProfile)
                ? newFilters.passProfile
                : 'all'
            );
          }

          if (newFilters.minConfidence !== undefined) {
            next.set(
              'conf',
              VALID_CONFIDENCE.includes(newFilters.minConfidence)
                ? newFilters.minConfidence
                : 'nominal'
            );
          }

          if (newFilters.h3Res !== undefined) {
            const resolution = newFilters.h3Res;

            if (
              Number.isInteger(resolution) &&
              resolution >= MIN_H3_RESOLUTION &&
              resolution <= MAX_H3_RESOLUTION
            ) {
              next.set('res', String(resolution));
            }
          }

          return next;
        },
        { replace: false }
      );
    },
    [setSearchParams]
  );

  return {
    filters,
    updateFilters,
  };
}

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

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: FilterState = useMemo(() => {
    const regionId = searchParams.get('region') || 'pwn';
    const startDate = searchParams.get('start') || '2020-01-01';
    const endDate = searchParams.get('end') || '2025-12-31';
    const sensorsRaw = searchParams.get('sensors');
    const sensors = sensorsRaw ? sensorsRaw.split(',') : ['MODIS', 'VIIRS'];
    const passProfile = (searchParams.get('pass') as 'all' | 'day' | 'night') || 'all';
    const minConfidence = (searchParams.get('conf') as 'all' | 'nominal' | 'high') || 'nominal';
    const h3Res = parseInt(searchParams.get('res') || '7', 10);

    return {
      regionId,
      startDate,
      endDate,
      sensors,
      passProfile,
      minConfidence,
      h3Res,
    };
  }, [searchParams]);

  const updateFilters = useCallback(
    (newFilters: Partial<FilterState>) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (newFilters.regionId !== undefined) next.set('region', newFilters.regionId);
        if (newFilters.startDate !== undefined) next.set('start', newFilters.startDate);
        if (newFilters.endDate !== undefined) next.set('end', newFilters.endDate);
        if (newFilters.sensors !== undefined) next.set('sensors', newFilters.sensors.join(','));
        if (newFilters.passProfile !== undefined) next.set('pass', newFilters.passProfile);
        if (newFilters.minConfidence !== undefined) next.set('conf', newFilters.minConfidence);
        if (newFilters.h3Res !== undefined) next.set('res', String(newFilters.h3Res));
        return next;
      });
    },
    [setSearchParams]
  );

  return {
    filters,
    updateFilters,
  };
}


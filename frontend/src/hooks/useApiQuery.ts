import { useState, useEffect, useCallback } from 'react';
import type { ApiResponse, ApiError } from '../api/types/common';

interface UseApiQueryResult<T> {
  data: T | null;
  meta: ApiResponse<T>['meta'] | null;
  isLoading: boolean;
  isError: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

export function useApiQuery<T>(
  queryFn: () => Promise<ApiResponse<T>>,
  deps: unknown[] = []
): UseApiQueryResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [meta, setMeta] = useState<ApiResponse<T>['meta'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const execute = useCallback(async () => {
    setIsLoading(true);
    setIsError(false);
    setError(null);
    try {
      const response = await queryFn();
      setData(response.data);
      setMeta(response.meta);
    } catch (err) {
      setIsError(true);
      setError(err as ApiError);
    } finally {
      setIsLoading(false);
    }
  }, [queryFn]);

  useEffect(() => {
    let ignore = false;

    async function loadData() {
      try {
        const response = await queryFn();
        if (!ignore) {
          setData(response.data);
          setMeta(response.meta);
          setIsLoading(false);
          setIsError(false);
          setError(null);
        }
      } catch (err) {
        if (!ignore) {
          setIsError(true);
          setError(err as ApiError);
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return {
    data,
    meta,
    isLoading,
    isError,
    error,
    refetch: execute,
  };
}

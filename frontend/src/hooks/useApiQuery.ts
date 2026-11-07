
import {
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';

import type {
  ApiResponse,
  ApiError,
} from '../api/types/common';

interface UseApiQueryResult<T> {
  data: T | null;
  meta: ApiResponse<T>['meta'] | null;
  isLoading: boolean;
  isError: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

function normalizeError(error: unknown): ApiError {
  if (
    typeof error === 'object' &&
    error !== null &&
    'error' in error
  ) {
    const candidate = error as ApiError;

    if (
      candidate.error &&
      typeof candidate.error.code === 'string' &&
      typeof candidate.error.message === 'string'
    ) {
      return candidate;
    }
  }

  if (error instanceof Error) {
    return {
      error: {
        code: 'REQUEST_FAILED',
        message: error.message,
      },
    };
  }

  return {
    error: {
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred while fetching data.',
    },
  };
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

  const queryFnRef = useRef(queryFn);
  const requestIdRef = useRef(0);
  const mountedRef = useRef(false);

  // Always use the latest query function.
  queryFnRef.current = queryFn;

  // Track component mounting and unmounting.
  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      requestIdRef.current += 1;
    };
  }, []);

  // Shared request logic for initial loading and manual refetching.
  const execute = useCallback(async () => {
    const requestId = ++requestIdRef.current;

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const response = await queryFnRef.current();

      // Ignore outdated responses and unmounted components.
      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      setData(response.data);
      setMeta(response.meta);
      setIsError(false);
      setError(null);
    } catch (err) {
      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      setIsError(true);
      setError(normalizeError(err));
    } finally {
      if (
        mountedRef.current &&
        requestId === requestIdRef.current
      ) {
        setIsLoading(false);
      }
    }
  }, []);

  // Automatically fetch when dependencies change.
  useEffect(() => {
    void execute();

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

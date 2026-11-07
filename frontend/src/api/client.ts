
import axios, {
  type AxiosRequestConfig,
  isAxiosError,
} from 'axios';

import type { ApiResponse, ApiError } from './types/common';

// --------------------------------------------------
// Configuration
// --------------------------------------------------

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  'http://127.0.0.1:8000/api/v1';

export const API_MODE: 'live' | 'mock' =
  import.meta.env.VITE_API_MODE === 'mock' ? 'mock' : 'live';

// --------------------------------------------------
// Axios instance
// --------------------------------------------------

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// --------------------------------------------------
// Error normalization
// --------------------------------------------------

function normalizeApiError(error: unknown): ApiError {
  if (isAxiosError(error)) {
    const responseData = error.response?.data as
      | {
          error?: {
            code?: string;
            message?: string;
            details?: Record<string, unknown>;
          };
          detail?: string;
        }
      | undefined;

    let code = 'network_error';
    let message =
      'Unable to connect to the TerraFlare backend.';
    let details: Record<string, unknown> = {};

    if (error.code === 'ECONNABORTED') {
      code = 'request_timeout';
      message = 'The API request timed out. Please try again.';
    } else if (error.response) {
      code =
        responseData?.error?.code ?? 'api_error';

      message =
        responseData?.error?.message ??
        responseData?.detail ??
        `Request failed with status ${error.response.status}.`;

      details = responseData?.error?.details ?? {};
    }

    return {
      error: {
        code,
        message,
        details,
      },
    };
  }

  return {
    error: {
      code: 'unknown_error',
      message:
        error instanceof Error
          ? error.message
          : 'An unexpected error occurred.',
      details: {},
    },
  };
}

// --------------------------------------------------
// Typed request helper
// --------------------------------------------------

export async function request<T>(
  config: AxiosRequestConfig,
  mockFallback?: () => T
): Promise<ApiResponse<T>> {

  // Explicit mock mode only
  if (API_MODE === 'mock') {
    if (!mockFallback) {
      throw normalizeApiError(
        new Error(
          'Mock mode is enabled, but no mock data is available for this endpoint.'
        )
      );
    }

    await new Promise((resolve) => setTimeout(resolve, 150));

    return {
      meta: {
        api_version: 'v1',
        data_version: 'frontend-mock',
        data_mode: 'fixture',
        is_synthetic: true,
        method_id: 'frontend-mock',
        generated_at: new Date().toISOString(),
        parameters: {},
        limitations: [
          'Frontend mock data is active.',
          'These values are illustrative and are not actual NASA observations.',
        ],
      },
      data: mockFallback(),
    };
  }

  // Live API mode
  try {
    const response = await apiClient.request<ApiResponse<T>>(config);
    return response.data;
  } catch (error) {
    const apiError = normalizeApiError(error);

    console.error(
      `[TerraFlare API] ${config.method ?? 'GET'} ${config.url} failed:`,
      apiError
    );

    throw apiError;
  }
}

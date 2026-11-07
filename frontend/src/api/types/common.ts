export interface ApiMeta {
  api_version: string;
  data_version: string;
  data_mode: 'fixture' | 'real';
  is_synthetic: boolean;
  method_id?: string;
  generated_at: string;
  parameters?: Record<string, unknown>;
  limitations?: string[];
}

export interface ApiResponse<T> {
  meta: ApiMeta;
  data: T;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}


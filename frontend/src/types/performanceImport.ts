export interface PerformanceImportError {
  field: string | null
  error_code: string
  message: string
}

export interface CalculatedMetricsPreview {
  ctr: string
  conversion_rate: string
  roi: string | null
}

export interface PerformancePreviewRow {
  row_number: number
  status: 'valid' | 'invalid'
  normalized_data: Record<string, unknown> | null
  calculated_metrics: CalculatedMetricsPreview | null
  errors: PerformanceImportError[]
}

export interface PerformanceImportPreview {
  total_rows: number
  valid_rows: number
  invalid_rows: number
  rows: PerformancePreviewRow[]
}

export interface PerformanceImportSuccessRow {
  row_number: number
  performance_record_id: number
}

export interface PerformanceImportFailureRow {
  row_number: number
  errors: PerformanceImportError[]
}

export interface PerformanceImportResult {
  total_rows: number
  success_count: number
  failure_count: number
  successes: PerformanceImportSuccessRow[]
  failures: PerformanceImportFailureRow[]
}


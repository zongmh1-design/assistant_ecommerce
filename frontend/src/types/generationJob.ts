import type { PaginatedResponse } from './api'

export type GenerationJobKind = 'image' | 'video'
export type GenerationJobStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'timeout'
export type GenerationJobEventType = 'created' | 'started' | 'succeeded' | 'failed' | 'retry_requested' | 'cancelled' | 'timeout'

export interface GenerationJobEvent {
  id: number
  job_id: number
  event_type: GenerationJobEventType
  event_message: string
  created_at: string
}

export interface GenerationJob {
  id: number
  product_id: number
  creative_plan_id: number
  job_kind: GenerationJobKind
  job_status: GenerationJobStatus
  attempts: number
  max_attempts: number
  locked_at: string | null
  locked_by: string | null
  next_run_at: string | null
  result_json: Record<string, unknown> | null
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface GenerationJobDetail extends GenerationJob {
  events: GenerationJobEvent[]
}

export type GenerationJobListResponse = PaginatedResponse<GenerationJob>

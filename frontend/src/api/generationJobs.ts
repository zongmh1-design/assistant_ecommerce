import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  GenerationJob,
  GenerationJobDetail,
  GenerationJobKind,
  GenerationJobListResponse,
  GenerationJobStatus,
} from '../types/generationJob'

export function createImageGenerationJob(productId: number, creativePlanId: number): Promise<GenerationJob> {
  return apiClient(`/products/${productId}/creative-plans/${creativePlanId}/images/generate`, { method: 'POST' })
}

export function createVideoGenerationJob(productId: number, creativePlanId: number): Promise<GenerationJob> {
  return apiClient(`/products/${productId}/creative-plans/${creativePlanId}/videos/generate`, { method: 'POST' })
}

export function listGenerationJobs(
  productId: number,
  query: PageQuery & { job_kind?: GenerationJobKind; job_status?: GenerationJobStatus } = {},
): Promise<GenerationJobListResponse> {
  return apiClient(`/products/${productId}/generation-jobs`, {}, query)
}

export function getGenerationJob(productId: number, jobId: number): Promise<GenerationJobDetail> {
  return apiClient(`/products/${productId}/generation-jobs/${jobId}`)
}

export function runGenerationJob(productId: number, jobId: number): Promise<GenerationJobDetail> {
  return apiClient(`/products/${productId}/generation-jobs/${jobId}/run`, { method: 'POST' })
}

export function retryGenerationJob(productId: number, jobId: number): Promise<GenerationJobDetail> {
  return apiClient(`/products/${productId}/generation-jobs/${jobId}/retry`, { method: 'POST' })
}

export function cancelGenerationJob(productId: number, jobId: number): Promise<GenerationJobDetail> {
  return apiClient(`/products/${productId}/generation-jobs/${jobId}/cancel`, { method: 'POST' })
}
